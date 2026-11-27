from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import httpx
from fastapi import status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.llm.router import LLMRouter
from app.models.escalation import EscalationStep
from app.models.promise import Promise
from app.schemas.escalation import (
    EscalationDraftData,
    EscalationDraftRequest,
    EscalationNextStepData,
)
from app.utils.exceptions import AppError, ErrorCode

IST = ZoneInfo("Asia/Kolkata")

_RUNG_METADATA: dict[int, tuple[str, str, str, str | None]] = {
    1: (
        "polite_nudge",
        "Polite Nudge",
        "Send a polite follow-up email referencing your order/claim and promised due date.",
        None,
    ),
    2: (
        "formal_grievance",
        "Formal Grievance Officer Notice",
        "Escalate formally to the company's Grievance Officer with a 7-day resolution deadline.",
        None,
    ),
    3: (
        "nch_draft",
        "National Consumer Helpline Complaint",
        "File a complaint draft on the National Consumer Helpline (NCH) / sector ombudsman.",
        "National Consumer Helpline (NCH)",
    ),
    4: (
        "consumer_commission",
        "Consumer Commission Notice",
        "Prepare a formal notice for filing before the Consumer Disputes Redressal Commission.",
        "District Consumer Disputes Redressal Commission",
    ),
}


class _DraftLLMResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    draft_text: str = Field(min_length=20)


def compute_rung_for_days_overdue(
    days_overdue: int,
    thresholds: list[int] | None = None,
) -> int:
    """
    Deterministic rung calculation from days_overdue and configurable thresholds [t1, t2, t3].
    Default thresholds [7, 21, 45]:
      0..7   -> Rung 1
      8..21  -> Rung 2
      22..45 -> Rung 3
      46+    -> Rung 4
    """
    t = thresholds if thresholds is not None else settings.ESCALATION_THRESHOLDS_DAYS
    t1, t2, t3 = t[0], t[1], t[2]
    if days_overdue <= t1:
        return 1
    if days_overdue <= t2:
        return 2
    if days_overdue <= t3:
        return 3
    return 4


def _compute_deadline(
    due_date: date | None,
    today_ist: date,
    rung: int,
    thresholds: list[int],
) -> date:
    if due_date is None:
        return today_ist + timedelta(days=7)
    t1, t2, t3 = thresholds[0], thresholds[1], thresholds[2]
    if rung == 1:
        target = due_date + timedelta(days=t1)
    elif rung == 2:
        target = due_date + timedelta(days=t2)
    elif rung == 3:
        target = due_date + timedelta(days=t3)
    else:
        target = today_ist + timedelta(days=14)
    return max(target, today_ist)


def _format_inr(amount_paise: int | None) -> str:
    if amount_paise is None:
        return "the promised amount"
    return f"Rs. {amount_paise / 100:,.2f}"


def _build_template_draft(
    promise: Promise,
    rung: int,
    tone: str,
    include_legal_references: bool,
) -> str:
    amount_str = _format_inr(promise.amount_paise)
    due_str = promise.due_date.isoformat() if promise.due_date else "the promised date"
    legal_line = (
        "\nUnder the Consumer Protection Act, 2019, failure to honor a committed refund/settlement "
        "constitutes a deficiency in service."
        if include_legal_references
        else ""
    )
    greeting = "Dear Support Team," if rung == 1 else f"Dear {promise.merchant_name} Grievance Officer,"
    tone_opening = (
        "I am writing to gently follow up regarding"
        if tone == "polite" and rung == 1
        else "I am writing to formally escalate"
    )

    return (
        f"Subject: Escalation (Rung {rung}) — Pending {promise.category or 'refund'} of "
        f"{amount_str} ({promise.merchant_name})\n\n"
        f"{greeting}\n\n"
        f"{tone_opening} my pending {promise.category or 'promise'} of {amount_str}, "
        f"which was due on {due_str}.\n\n"
        f'Reference quote from your communication:\n"{promise.exact_quote}"\n'
        f"{legal_line}\n\n"
        "Please process this payment and share the transaction reference number at the earliest.\n\n"
        "Sincerely,\n[Your Name]"
    )


async def _get_owned_promise(db: AsyncSession, user_id: UUID, promise_id: UUID) -> Promise:
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
    return promise


async def get_next_escalation_step(
    db: AsyncSession,
    user_id: UUID,
    promise_id: UUID,
    *,
    today_ist: date | None = None,
    thresholds: list[int] | None = None,
) -> EscalationNextStepData:
    """Compute deterministic next escalation rung and deadline in IST (Asia/Kolkata)."""
    promise = await _get_owned_promise(db, user_id, promise_id)
    active_thresholds = thresholds or settings.ESCALATION_THRESHOLDS_DAYS
    ref_today = today_ist or datetime.now(IST).date()

    days_overdue = (
        max(0, (ref_today - promise.due_date).days) if promise.due_date is not None else 0
    )
    next_rung = compute_rung_for_days_overdue(days_overdue, active_thresholds)

    existing_steps = (
        await db.execute(
            select(EscalationStep)
            .where(EscalationStep.promise_id == promise.id)
            .order_by(EscalationStep.rung.asc())
        )
    ).scalars().all()
    current_rung = max((s.rung for s in existing_steps), default=None)

    notice_type, rung_name, rung_desc, default_forum = _RUNG_METADATA[next_rung]
    legal_forum = default_forum
    if next_rung == 3 and promise.category == "insurance":
        legal_forum = "Insurance Ombudsman"

    deadline_date = _compute_deadline(promise.due_date, ref_today, next_rung, active_thresholds)
    days_until = (deadline_date - ref_today).days

    # Upsert the escalation_step record for this rung if not yet recorded
    if not any(s.rung == next_rung for s in existing_steps):
        db.add(
            EscalationStep(
                id=uuid4(),
                promise_id=promise.id,
                rung=next_rung,
                deadline=deadline_date,
                notice_type=notice_type,
            )
        )
        await db.commit()

    return EscalationNextStepData(
        promise_id=promise.id,
        current_rung=current_rung,
        next_rung=next_rung,
        rung_name=rung_name,
        rung_description=rung_desc,
        deadline_date=deadline_date,
        days_until_deadline=days_until,
        legal_forum=legal_forum,
    )


async def generate_escalation_draft(
    db: AsyncSession,
    user_id: UUID,
    promise_id: UUID,
    req: EscalationDraftRequest,
    *,
    router: LLMRouter | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> EscalationDraftData:
    """Generate an escalation draft via LLM with deterministic template fallback."""
    promise = await _get_owned_promise(db, user_id, promise_id)
    notice_type, rung_name, _, _ = _RUNG_METADATA[req.rung]

    prompt = (
        "Draft a consumer escalation message in strict JSON: "
        '{"draft_text": "<message>"}.\n'
        f"Merchant: {promise.merchant_name}\n"
        f"Category: {promise.category or 'refund'}\n"
        f"Amount: {_format_inr(promise.amount_paise)}\n"
        f"Due Date: {promise.due_date.isoformat() if promise.due_date else 'N/A'}\n"
        f"Exact Quote: {promise.exact_quote}\n"
        f"Escalation Rung: {req.rung} ({rung_name})\n"
        f"Tone: {req.tone}\n"
        f"Include Indian Consumer Protection Act references: {req.include_legal_references}\n"
        "Keep it clear, factual, and polite/firm as requested."
    )

    active_router = router or LLMRouter()
    llm_res = await active_router.call_json(
        prompt,
        _DraftLLMResponse,
        db=db,
        http_client=http_client,
    )

    if llm_res is not None:
        draft_text = llm_res.data.draft_text.strip()
        model_used = llm_res.model
    else:
        draft_text = _build_template_draft(
            promise, req.rung, req.tone, req.include_legal_references
        )
        model_used = "deterministic-template"

    notice = settings.NOT_LEGAL_ADVICE_TEXT
    if notice not in draft_text:
        full_saved_text = f"{draft_text}\n\n---\n{notice}"
    else:
        full_saved_text = draft_text

    now = datetime.now(UTC)
    existing_step = (
        await db.execute(
            select(EscalationStep).where(
                EscalationStep.promise_id == promise.id,
                EscalationStep.rung == req.rung,
            )
        )
    ).scalar_one_or_none()

    if existing_step is None:
        db.add(
            EscalationStep(
                id=uuid4(),
                promise_id=promise.id,
                rung=req.rung,
                deadline=datetime.now(IST).date() + timedelta(days=7),
                draft_text=full_saved_text,
                draft_generated_at=now,
                notice_type=notice_type,
            )
        )
    else:
        existing_step.draft_text = full_saved_text
        existing_step.draft_generated_at = now
    await db.commit()

    return EscalationDraftData(
        draft_text=draft_text,
        rung=req.rung,
        not_legal_advice_notice=notice,
        generated_at=now,
        model_used=model_used,
    )
