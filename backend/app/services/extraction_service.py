from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.guard import (
    detect_prompt_injection,
    is_amount_in_quote,
    is_quote_literal_substring,
    parse_iso_due_date,
)
from app.llm.prompts import build_extraction_prompt
from app.llm.providers.deterministic import (
    ExtractedPromiseCandidate,
    ExtractionLLMResponse,
    PromiseCategory,
    deterministic_extract_promises,
)
from app.llm.router import LLMRouter

ExtractionMethod = Literal["llm", "deterministic"]
InitialStatus = Literal["pending", "needs_review"]


@dataclass(frozen=True)
class ValidatedPromiseCandidate:
    merchant: str
    amount_paise: int | None
    due_date: date | None
    exact_quote: str
    confidence: float
    category: PromiseCategory
    status: InitialStatus
    extraction_method: ExtractionMethod
    needs_review_reason: str | None


def validate_candidate(
    candidate: ExtractedPromiseCandidate,
    email_body: str,
    extraction_method: ExtractionMethod,
) -> ValidatedPromiseCandidate:
    """Apply deterministic code-level validation checks to an extracted candidate."""
    reasons: list[str] = []
    confidence = candidate.confidence

    if detect_prompt_injection(email_body) or detect_prompt_injection(candidate.exact_quote):
        reasons.append("Possible prompt injection detected")
        confidence = 0.0

    if not is_quote_literal_substring(candidate.exact_quote, email_body):
        reasons.append("exact_quote is not a literal substring of email body")
        confidence = 0.0

    if not is_amount_in_quote(candidate.amount_inr, candidate.exact_quote):
        reasons.append("Extracted amount not found in exact_quote")

    parsed_date, date_ok = parse_iso_due_date(candidate.due_date)
    if not date_ok:
        reasons.append("Unparseable due_date")

    if not reasons and confidence < 0.6:
        reasons.append("Low extraction confidence")

    amount_paise = (
        round(float(candidate.amount_inr) * 100) if candidate.amount_inr is not None else None
    )
    status: InitialStatus = "needs_review" if reasons else "pending"
    needs_review_reason = "; ".join(reasons) if reasons else None

    return ValidatedPromiseCandidate(
        merchant=candidate.merchant.strip(),
        amount_paise=amount_paise,
        due_date=parsed_date,
        exact_quote=candidate.exact_quote.strip(),
        confidence=confidence,
        category=candidate.category,
        status=status,
        extraction_method=extraction_method,
        needs_review_reason=needs_review_reason,
    )


async def extract_promises(
    email_body: str,
    *,
    sender: str = "",
    received_at: datetime | None = None,
    db: AsyncSession | None = None,
    router: LLMRouter | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> list[ValidatedPromiseCandidate]:
    """Extract and validate promise candidates from an email body with deterministic fallback."""
    active_router = router or LLMRouter()
    prompt = build_extraction_prompt(
        email_body=email_body,
        sender=sender,
        received_at=received_at.isoformat() if received_at else "",
    )

    llm_result = await active_router.call_json(
        prompt,
        ExtractionLLMResponse,
        db=db,
        http_client=http_client,
    )

    if llm_result is not None:
        method: ExtractionMethod = "llm"
        raw_candidates = llm_result.data.promises
    else:
        method = "deterministic"
        raw_candidates = deterministic_extract_promises(
            email_body, sender=sender, received_at=received_at
        ).promises

    return [validate_candidate(c, email_body, method) for c in raw_candidates]
