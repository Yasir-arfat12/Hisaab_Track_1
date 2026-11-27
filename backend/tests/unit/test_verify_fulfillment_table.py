import hashlib
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import BankCredit, VerificationMatch
from app.models.promise import Merchant, Promise
from app.models.user import User
from app.services.verification_service import verify_fulfillment


@pytest.mark.parametrize(
    ("case_name", "expected_paise", "credits_spec", "claim_first_credit", "expected_status"),
    [
        (
            "exact_match",
            249900,
            [(249900, 0, "FLIPKART REFUND REF FKT001")],
            False,
            "kept",
        ),
        (
            "partial_refund",
            320000,
            [(290000, 1, "FLIPKART PARTIAL REFUND REF FKT002")],
            False,
            "needs_review",
        ),
        (
            "duplicate_charge",
            50000,
            [(50000, 0, "FLIPKART REFUND REF FKT003")],
            True,
            "needs_review",
        ),
        (
            "ambiguous_match",
            100000,
            [
                (100000, 0, "FLIPKART REFUND REF FKT004A"),
                (100000, 1, "FLIPKART REFUND REF FKT004B"),
            ],
            False,
            "needs_review",
        ),
        (
            "wrong_merchant",
            249900,
            [(249900, 0, "SWIGGY ORDER REFUND REF SWG005")],
            False,
            "pending",
        ),
    ],
)
async def test_verify_fulfillment_table_driven(
    db_session: AsyncSession,
    case_name: str,
    expected_paise: int,
    credits_spec: list[tuple[int, int, str]],
    claim_first_credit: bool,
    expected_status: str,
) -> None:
    user = User(id=uuid4(), email=f"{case_name}@example.com", name="Test User", is_demo=False)
    merchant = Merchant(
        id=uuid4(),
        name="Flipkart",
        normalized_name=f"flipkart_{case_name}",
        domain="flipkart.com",
    )
    db_session.add_all([user, merchant])
    await db_session.flush()

    due = date(2026, 11, 20)
    promise = Promise(
        id=uuid4(),
        user_id=user.id,
        merchant_id=merchant.id,
        merchant_name="Flipkart",
        category="refund",
        amount_paise=expected_paise,
        due_date=due,
        exact_quote="Your Flipkart refund will be credited.",
        confidence=0.95,
        status="pending",
        extraction_method="llm",
    )
    db_session.add(promise)
    await db_session.flush()

    created_credits: list[BankCredit] = []
    for idx, (amt, day_offset, narration) in enumerate(credits_spec):
        cred_dt = datetime.combine(
            due + timedelta(days=day_offset), datetime.min.time(), tzinfo=UTC
        )
        c_hash = hashlib.sha256(f"{case_name}:{idx}:{amt}:{narration}".encode()).hexdigest()
        credit = BankCredit(
            id=uuid4(),
            user_id=user.id,
            source="csv",
            amount_paise=amt,
            credited_at=cred_dt,
            narration=narration,
            credit_hash=c_hash,
        )
        db_session.add(credit)
        created_credits.append(credit)
    await db_session.flush()

    if claim_first_credit:
        other_promise = Promise(
            id=uuid4(),
            user_id=user.id,
            merchant_id=merchant.id,
            merchant_name="Flipkart",
            category="refund",
            amount_paise=expected_paise,
            due_date=due,
            exact_quote="Earlier Flipkart refund.",
            confidence=0.95,
            status="kept",
            extraction_method="llm",
        )
        db_session.add(other_promise)
        await db_session.flush()
        db_session.add(
            VerificationMatch(
                id=uuid4(),
                promise_id=other_promise.id,
                credit_id=created_credits[0].id,
                match_score=1.0,
                is_ambiguous=False,
            )
        )

    await db_session.commit()

    result = await verify_fulfillment(db_session, user.id, promise.id)
    assert result.new_status == expected_status

    matches = (
        await db_session.execute(
            select(VerificationMatch).where(VerificationMatch.promise_id == promise.id)
        )
    ).scalars().all()
    if expected_status == "kept":
        assert len(matches) == 1
        assert matches[0].is_ambiguous is False
    elif expected_status == "needs_review":
        assert len(matches) >= 1
        assert all(m.is_ambiguous is True for m in matches)
    else:
        assert len(matches) == 0
