import re
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PromiseCategory = Literal["refund", "delivery_credit", "insurance", "ticket", "other"]


class ExtractedPromiseCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    merchant: str = Field(min_length=1, max_length=255)
    amount_inr: float | int | None = Field(default=None, ge=0)
    due_date: str | None = None
    exact_quote: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    category: PromiseCategory = "other"


class ExtractionLLMResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    promises: list[ExtractedPromiseCandidate] = Field(default_factory=list)


_AMOUNT_RE = re.compile(
    r"(?:₹|Rs\.?|INR)\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)",
    re.IGNORECASE,
)
_ISO_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_DMY_DATE_RE = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")
_WITHIN_DAYS_RE = re.compile(
    r"within\s+(\d{1,2})\s+(?:business\s+|working\s+)?days",
    re.IGNORECASE,
)
_PROMISE_KEYWORDS_RE = re.compile(
    r"\b(refund|claim|settlement|credit(?:ed)?|reimburse(?:ment)?|deposit|reversal)\b",
    re.IGNORECASE,
)


def _infer_merchant(sender: str, quote: str) -> str:
    if "@" in sender:
        domain = sender.split("@", 1)[1].split(">", 1)[0].strip()
        root = domain.split(".")[0]
        if root and root.lower() not in {"gmail", "yahoo", "outlook", "mail", "noreply"}:
            return root.capitalize()
    for word in quote.split():
        cleaned = word.strip(".,:;!?()[]{}")
        if cleaned.istitle() and len(cleaned) > 2 and cleaned.lower() not in {"Your", "The", "We"}:
            return cleaned
    return "Unknown Merchant"


def _infer_category(text: str) -> PromiseCategory:
    low = text.lower()
    if "insurance" in low or "claim" in low:
        return "insurance"
    if "delivery" in low:
        return "delivery_credit"
    if "ticket" in low or "irctc" in low or "flight" in low or "bookmyshow" in low:
        return "ticket"
    if "refund" in low or "reimburse" in low or "reversal" in low:
        return "refund"
    return "other"


def _infer_due_date(quote: str, reference_date: date) -> str | None:
    iso_m = _ISO_DATE_RE.search(quote)
    if iso_m:
        return iso_m.group(1)

    dmy_m = _DMY_DATE_RE.search(quote)
    if dmy_m:
        day, month, year = int(dmy_m.group(1)), int(dmy_m.group(2)), int(dmy_m.group(3))
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            return None

    within_m = _WITHIN_DAYS_RE.search(quote)
    if within_m:
        days = int(within_m.group(1))
        return (reference_date + timedelta(days=days)).isoformat()

    return None


def deterministic_extract_promises(
    email_body: str,
    sender: str = "",
    received_at: datetime | None = None,
) -> ExtractionLLMResponse:
    """Regex-based fallback promise extractor when all LLM providers are unavailable."""
    ref_date = (received_at or datetime.now(UTC)).date()
    sentences = [
        s.strip()
        for s in re.split(r"(?<!Rs\.)(?<!No\.)(?<=[.!?])\s+|\n+", email_body)
        if s.strip()
    ]

    candidates: list[ExtractedPromiseCandidate] = []
    for sentence in sentences:
        if not _PROMISE_KEYWORDS_RE.search(sentence):
            continue
        amt_m = _AMOUNT_RE.search(sentence)
        if not amt_m:
            continue
        amount_inr = float(amt_m.group(1).replace(",", ""))
        due_date = _infer_due_date(sentence, ref_date)
        merchant = _infer_merchant(sender, sentence)
        category = _infer_category(sentence)
        candidates.append(
            ExtractedPromiseCandidate(
                merchant=merchant,
                amount_inr=amount_inr,
                due_date=due_date,
                exact_quote=sentence,
                confidence=0.65,
                category=category,
            )
        )

    return ExtractionLLMResponse(promises=candidates)
