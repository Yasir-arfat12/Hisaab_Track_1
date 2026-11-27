import hashlib
import re
from dataclasses import dataclass
from datetime import datetime

_BANK_ALERT_RE = re.compile(
    r"\b(credit\s+alert|credited\s+to\b|has\s+been\s+credited|neft\s+cr|imps\s+cr|upi\s+cr)\b",
    re.IGNORECASE,
)
_FUTURE_PROMISE_RE = re.compile(r"\bwill\s+be\s+credited\b", re.IGNORECASE)
_AMOUNT_RE = re.compile(
    r"(?:₹|Rs\.?|INR)\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)",
    re.IGNORECASE,
)
_REF_RE = re.compile(
    r"(?:ref(?:erence)?(?:\s*no\.?)?|utr|txn)[:\s#-]*([A-Z0-9]{6,24})",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ParsedBankAlert:
    amount_paise: int
    credited_at: datetime
    narration: str
    reference_number: str | None


def compute_body_hash(body_text: str) -> str:
    return hashlib.sha256(body_text.encode("utf-8", errors="replace")).hexdigest()


def parse_bank_alert_email(
    *,
    sender: str,
    subject: str,
    body_text: str,
    received_at: datetime,
) -> ParsedBankAlert | None:
    """Parse a bank credit alert email into a structured credit record, or None if not an alert."""
    combined = f"{subject}\n{body_text}"
    if _FUTURE_PROMISE_RE.search(combined) or not _BANK_ALERT_RE.search(combined):
        return None

    amt_match = _AMOUNT_RE.search(combined)
    if not amt_match:
        return None

    amount_inr = float(amt_match.group(1).replace(",", ""))
    if amount_inr <= 0:
        return None

    ref_match = _REF_RE.search(combined)
    ref_no = ref_match.group(1) if ref_match else None
    narration = " ".join(subject.split())[:200]
    if body_text.strip():
        first_line = " ".join(body_text.strip().splitlines()[0].split())
        narration = f"{narration} | {first_line}"[:400]

    return ParsedBankAlert(
        amount_paise=round(amount_inr * 100),
        credited_at=received_at,
        narration=narration,
        reference_number=ref_no,
    )
