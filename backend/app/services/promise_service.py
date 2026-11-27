from datetime import UTC, date, datetime
from typing import cast
from uuid import UUID, uuid5

from fastapi import status
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email import Email
from app.models.escalation import EscalationStep
from app.models.finance import BankCredit, VerificationMatch
from app.models.promise import Promise
from app.schemas.dashboard import DashboardCounts, DashboardSummaryData
from app.schemas.promise import (
    ExtractionMethod,
    PromiseDetail,
    PromiseListData,
    PromisePatchRequest,
    PromiseStatus,
    PromiseSummary,
    TimelineEvent,
)
from app.utils.exceptions import AppError, ErrorCode
from app.utils.pagination import decode_cursor, encode_cursor

TIMELINE_NS = UUID("11111111-1111-1111-1111-111111111111")


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _to_summary(p: Promise) -> PromiseSummary:
    return PromiseSummary(
        promise_id=p.id,
        merchant_name=p.merchant_name,
        merchant_id=p.merchant_id,
        category=p.category,
        amount_paise=p.amount_paise,
        status=cast(PromiseStatus, p.status),
        due_date=p.due_date,
        created_at=_to_utc(p.created_at),
    )


async def list_promises(
    db: AsyncSession,
    user_id: UUID,
    *,
    promise_status: PromiseStatus | None = None,
    category: str | None = None,
    merchant_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 20,
    cursor: str | None = None,
) -> PromiseListData:
    stmt = select(Promise).where(Promise.user_id == user_id)

    if promise_status is not None:
        stmt = stmt.where(Promise.status == promise_status)
    if category is not None:
        stmt = stmt.where(Promise.category == category)
    if merchant_id is not None:
        stmt = stmt.where(Promise.merchant_id == merchant_id)
    if date_from is not None:
        stmt = stmt.where(Promise.due_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(Promise.due_date <= date_to)

    if cursor is not None:
        c_created_at, c_id = decode_cursor(cursor)
        stmt = stmt.where(
            or_(
                Promise.created_at < c_created_at,
                and_(Promise.created_at == c_created_at, Promise.id < c_id),
            )
        )

    stmt = stmt.order_by(Promise.created_at.desc(), Promise.id.desc()).limit(limit + 1)
    rows = list((await db.execute(stmt)).scalars().all())

    has_more = len(rows) > limit
    page_rows = rows[:limit]
    next_cursor = (
        encode_cursor(_to_utc(page_rows[-1].created_at), page_rows[-1].id)
        if has_more and page_rows
        else None
    )

    return PromiseListData(
        items=[_to_summary(p) for p in page_rows],
        next_cursor=next_cursor,
        prev_cursor=None,
        limit=limit,
    )


async def _get_owned_promise(db: AsyncSession, user_id: UUID, promise_id: UUID) -> Promise:
    res = await db.execute(
        select(Promise).where(Promise.id == promise_id, Promise.user_id == user_id)
    )
    promise = res.scalar_one_or_none()
    if promise is None:
        raise AppError(
            code=ErrorCode.PROMISE_NOT_FOUND,
            message="The given promise_id does not exist",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"promise_id": str(promise_id)},
        )
    return promise


async def get_promise_detail(
    db: AsyncSession,
    user_id: UUID,
    promise_id: UUID,
) -> PromiseDetail:
    p = await _get_owned_promise(db, user_id, promise_id)

    source_email_id: str | None = None
    source_email_subject: str | None = None
    if p.email_id is not None:
        email_row = (
            await db.execute(select(Email).where(Email.id == p.email_id))
        ).scalar_one_or_none()
        if email_row is not None:
            source_email_id = email_row.gmail_message_id
            source_email_subject = email_row.subject

    matches_res = await db.execute(
        select(VerificationMatch, BankCredit)
        .join(BankCredit, VerificationMatch.credit_id == BankCredit.id)
        .where(VerificationMatch.promise_id == p.id)
        .order_by(VerificationMatch.matched_at.asc())
    )
    matches = matches_res.all()
    received_amount_paise: int | None = None
    if matches:
        received_amount_paise = sum(credit.amount_paise for _, credit in matches)

    esc_res = await db.execute(
        select(EscalationStep)
        .where(EscalationStep.promise_id == p.id)
        .order_by(EscalationStep.rung.asc())
    )
    esc_steps = list(esc_res.scalars().all())
    escalation_rung = max((step.rung for step in esc_steps), default=None)

    timeline: list[TimelineEvent] = [
        TimelineEvent(
            event_id=str(uuid5(TIMELINE_NS, f"{p.id}:extracted")),
            type="promise_extracted",
            description="Promise extracted from email",
            occurred_at=_to_utc(p.created_at),
            metadata={"confidence_score": p.confidence, "method": p.extraction_method},
        )
    ]

    if p.status == "overdue" and p.due_date is not None:
        overdue_dt = datetime.combine(p.due_date, datetime.min.time(), tzinfo=UTC)
        timeline.append(
            TimelineEvent(
                event_id=str(uuid5(TIMELINE_NS, f"{p.id}:overdue")),
                type="overdue_detected",
                description="Due date passed without matching bank credit",
                occurred_at=overdue_dt,
                metadata=None,
            )
        )

    for match, credit in matches:
        timeline.append(
            TimelineEvent(
                event_id=str(uuid5(TIMELINE_NS, f"{p.id}:match:{match.id}")),
                type="credit_matched",
                description=f"Matched bank credit: {credit.narration}",
                occurred_at=_to_utc(match.matched_at),
                metadata={
                    "credit_id": str(credit.id),
                    "amount_paise": credit.amount_paise,
                    "is_ambiguous": match.is_ambiguous,
                },
            )
        )

    for step in esc_steps:
        timeline.append(
            TimelineEvent(
                event_id=str(uuid5(TIMELINE_NS, f"{p.id}:esc:{step.rung}")),
                type="escalation_advanced",
                description=f"Escalation advanced to rung {step.rung}",
                occurred_at=_to_utc(step.created_at),
                metadata={"rung": step.rung, "notice_type": step.notice_type},
            )
        )

    if p.dismissed_at is not None:
        timeline.append(
            TimelineEvent(
                event_id=str(uuid5(TIMELINE_NS, f"{p.id}:dismissed")),
                type="status_changed",
                description="Promise marked as dismissed",
                occurred_at=_to_utc(p.dismissed_at),
                metadata={"status": "dismissed"},
            )
        )

    timeline.sort(key=lambda evt: evt.occurred_at)

    return PromiseDetail(
        promise_id=p.id,
        merchant_name=p.merchant_name,
        merchant_id=p.merchant_id,
        category=p.category,
        amount_paise=p.amount_paise,
        status=cast(PromiseStatus, p.status),
        due_date=p.due_date,
        created_at=_to_utc(p.created_at),
        received_amount_paise=received_amount_paise,
        source_email_id=source_email_id,
        source_email_subject=source_email_subject,
        user_note=p.user_note,
        escalation_rung=escalation_rung,
        exact_quote=p.exact_quote,
        confidence=p.confidence,
        extraction_method=cast(ExtractionMethod, p.extraction_method),
        needs_review_reason=p.needs_review_reason,
        updated_at=_to_utc(p.updated_at),
        timeline=timeline,
    )


async def patch_promise(
    db: AsyncSession,
    user_id: UUID,
    promise_id: UUID,
    patch: PromisePatchRequest,
) -> PromiseSummary:
    p = await _get_owned_promise(db, user_id, promise_id)

    if patch.status == "dismissed":
        p.status = "dismissed"
        p.dismissed_at = datetime.now(UTC)
    if patch.user_note is not None:
        p.user_note = patch.user_note

    p.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(p)
    return _to_summary(p)


async def get_dashboard_summary(db: AsyncSession, user_id: UUID) -> DashboardSummaryData:
    stmt = select(
        func.count(Promise.id).label("total"),
        func.coalesce(
            func.sum(case((Promise.status == "pending", 1), else_=0)), 0
        ).label("pending"),
        func.coalesce(
            func.sum(case((Promise.status == "kept", 1), else_=0)), 0
        ).label("kept"),
        func.coalesce(
            func.sum(case((Promise.status == "overdue", 1), else_=0)), 0
        ).label("overdue"),
        func.coalesce(
            func.sum(case((Promise.status == "needs_review", 1), else_=0)), 0
        ).label("needs_review"),
        func.coalesce(
            func.sum(case((Promise.status == "dismissed", 1), else_=0)), 0
        ).label("dismissed"),
        func.coalesce(
            func.sum(
                case(
                    (
                        Promise.status.in_(["pending", "overdue", "needs_review"]),
                        func.coalesce(Promise.amount_paise, 0),
                    ),
                    else_=0,
                )
            ),
            0,
        ).label("total_owed_paise"),
        func.coalesce(
            func.sum(
                case(
                    (Promise.status == "overdue", func.coalesce(Promise.amount_paise, 0)),
                    else_=0,
                )
            ),
            0,
        ).label("total_overdue_paise"),
        func.coalesce(
            func.sum(
                case(
                    (Promise.status == "kept", func.coalesce(Promise.amount_paise, 0)),
                    else_=0,
                )
            ),
            0,
        ).label("total_kept_paise"),
    ).where(Promise.user_id == user_id)

    row = (await db.execute(stmt)).one()
    return DashboardSummaryData(
        total_owed_paise=int(row.total_owed_paise),
        total_overdue_paise=int(row.total_overdue_paise),
        total_kept_paise=int(row.total_kept_paise),
        counts=DashboardCounts(
            total=int(row.total),
            pending=int(row.pending),
            kept=int(row.kept),
            overdue=int(row.overdue),
            needs_review=int(row.needs_review),
            dismissed=int(row.dismissed),
        ),
        computed_at=datetime.now(UTC),
    )
