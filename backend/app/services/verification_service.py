from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import BankCredit, VerificationMatch
from app.models.promise import Promise
from app.schemas.finance import PromiseStatus, VerifyResultData
from app.utils.exceptions import AppError, ErrorCode
from app.utils.fuzzy import merchant_match_score

MERCHANT_MATCH_THRESHOLD = 85.0
DATE_WINDOW_DAYS = 7


def _to_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


async def verify_fulfillment(
    db: AsyncSession,
    user_id: UUID,
    promise_id: UUID,
) -> VerifyResultData:
    """
    Deterministic code-only verification of a promise against bank_credits.
    Never auto-closes ambiguous or partial matches.
    """
    promise = (
        await db.execute(
            select(Promise).where(Promise.id == promise_id, Promise.user_id == user_id)
        )
    ).scalar_one_or_none()
    if promise is None:
        raise AppError(
            code=ErrorCode.PROMISE_NOT_FOUND,
            message="The given promise_id does not exist",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"promise_id": str(promise_id)},
        )

    previous_status = cast(PromiseStatus, promise.status)
    now = datetime.now(UTC)

    # Dismissed or amount-less promises are never auto-closed
    if promise.status == "dismissed" or promise.amount_paise is None:
        return VerifyResultData(
            promise_id=promise.id,
            previous_status=previous_status,
            new_status=previous_status,
            matched_credit_id=None,
            amount_paise_expected=promise.amount_paise,
            amount_paise_received=None,
            verified_at=now,
        )

    if promise.due_date is not None:
        window_start = datetime.combine(
            promise.due_date - timedelta(days=DATE_WINDOW_DAYS),
            datetime.min.time(),
            tzinfo=UTC,
        )
        window_end = datetime.combine(
            promise.due_date + timedelta(days=DATE_WINDOW_DAYS),
            datetime.max.time(),
            tzinfo=UTC,
        )
    else:
        created = _to_utc(promise.created_at)
        window_start = created - timedelta(days=1)
        window_end = created + timedelta(days=30)

    credits_res = await db.execute(
        select(BankCredit).where(
            BankCredit.user_id == user_id,
            BankCredit.credited_at >= window_start,
            BankCredit.credited_at <= window_end,
        )
    )
    window_credits = list(credits_res.scalars().all())

    # Filter by fuzzy merchant match >= 85%
    merchant_credits: list[tuple[BankCredit, float]] = []
    for credit in window_credits:
        score = merchant_match_score(credit.narration, promise.merchant_name)
        if score >= MERCHANT_MATCH_THRESHOLD:
            merchant_credits.append((credit, score))

    exact_matches = [
        (c, s) for c, s in merchant_credits if c.amount_paise == promise.amount_paise
    ]

    matched_credit_id: UUID | None = None
    amount_received: int | None = None

    if len(exact_matches) == 1:
        credit, score = exact_matches[0]
        # Check if this credit was already claimed by another promise
        claimed_other = (
            await db.execute(
                select(VerificationMatch).where(
                    VerificationMatch.credit_id == credit.id,
                    VerificationMatch.promise_id != promise.id,
                    VerificationMatch.is_ambiguous.is_(False),
                )
            )
        ).scalar_one_or_none()

        existing = (
            await db.execute(
                select(VerificationMatch).where(
                    VerificationMatch.promise_id == promise.id,
                    VerificationMatch.credit_id == credit.id,
                )
            )
        ).scalar_one_or_none()

        if claimed_other is not None:
            # Duplicate / already-claimed credit -> ambiguous, never auto-close
            if existing is None:
                db.add(
                    VerificationMatch(
                        id=uuid4(),
                        promise_id=promise.id,
                        credit_id=credit.id,
                        match_score=score / 100.0,
                        is_ambiguous=True,
                    )
                )
            promise.status = "needs_review"
            promise.needs_review_reason = (
                "Matching bank credit is already linked to another promise"
            )
        else:
            if existing is None:
                db.add(
                    VerificationMatch(
                        id=uuid4(),
                        promise_id=promise.id,
                        credit_id=credit.id,
                        match_score=score / 100.0,
                        is_ambiguous=False,
                    )
                )
            else:
                existing.is_ambiguous = False
            promise.status = "kept"
            promise.needs_review_reason = None

        matched_credit_id = credit.id
        amount_received = credit.amount_paise

    elif len(exact_matches) > 1:
        # Ambiguous: multiple credits match -> never auto-close
        for credit, score in exact_matches:
            existing = (
                await db.execute(
                    select(VerificationMatch).where(
                        VerificationMatch.promise_id == promise.id,
                        VerificationMatch.credit_id == credit.id,
                    )
                )
            ).scalar_one_or_none()
            if existing is None:
                db.add(
                    VerificationMatch(
                        id=uuid4(),
                        promise_id=promise.id,
                        credit_id=credit.id,
                        match_score=score / 100.0,
                        is_ambiguous=True,
                    )
                )
        promise.status = "needs_review"
        promise.needs_review_reason = (
            "Multiple matching bank credits found; please confirm manually"
        )
        matched_credit_id = exact_matches[0][0].id
        amount_received = exact_matches[0][0].amount_paise

    else:
        # Check for partial refund (0 < credit.amount_paise < promise.amount_paise)
        partial_matches = [
            (c, s) for c, s in merchant_credits if 0 < c.amount_paise < promise.amount_paise
        ]
        if partial_matches:
            credit, score = partial_matches[0]
            existing = (
                await db.execute(
                    select(VerificationMatch).where(
                        VerificationMatch.promise_id == promise.id,
                        VerificationMatch.credit_id == credit.id,
                    )
                )
            ).scalar_one_or_none()
            if existing is None:
                db.add(
                    VerificationMatch(
                        id=uuid4(),
                        promise_id=promise.id,
                        credit_id=credit.id,
                        match_score=score / 100.0,
                        is_ambiguous=True,
                    )
                )
            promise.status = "needs_review"
            promise.needs_review_reason = (
                f"Partial refund detected: {credit.amount_paise} of "
                f"{promise.amount_paise} paise received"
            )
            matched_credit_id = credit.id
            amount_received = credit.amount_paise

    promise.updated_at = now
    await db.commit()
    await db.refresh(promise)

    return VerifyResultData(
        promise_id=promise.id,
        previous_status=previous_status,
        new_status=cast(PromiseStatus, promise.status),
        matched_credit_id=matched_credit_id,
        amount_paise_expected=promise.amount_paise,
        amount_paise_received=amount_received,
        verified_at=now,
    )
