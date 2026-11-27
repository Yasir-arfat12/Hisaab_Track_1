import re
from datetime import date

INJECTION_PATTERNS = (
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?prior\s+instructions", re.IGNORECASE),
    re.compile(r"system\s+prompt", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(a|an)", re.IGNORECASE),
)


def detect_prompt_injection(text: str) -> bool:
    """Return True if known prompt-injection phrases appear in text."""
    return any(pattern.search(text) for pattern in INJECTION_PATTERNS)


def is_quote_literal_substring(exact_quote: str, body_text: str) -> bool:
    """Return True if exact_quote (stripped) is a literal substring of body_text."""
    cleaned = exact_quote.strip()
    if not cleaned:
        return False
    return cleaned in body_text


def is_amount_in_quote(amount_inr: float | None, exact_quote: str) -> bool:
    """Return True if amount_inr is None or its numeric digits appear inside exact_quote."""
    if amount_inr is None:
        return True

    # Extract all numbers (with optional commas and decimals) from the quote
    raw_numbers = re.findall(r"\d[\d,]*(?:\.\d+)?", exact_quote)
    target = round(float(amount_inr), 2)
    for token in raw_numbers:
        try:
            val = round(float(token.replace(",", "")), 2)
        except ValueError:
            continue
        if abs(val - target) < 0.01:
            return True
    return False


def parse_iso_due_date(due_date_str: str | None) -> tuple[date | None, bool]:
    """Parse YYYY-MM-DD date string. Returns (parsed_date, is_valid)."""
    if due_date_str is None or not due_date_str.strip():
        return None, True
    try:
        return date.fromisoformat(due_date_str.strip()), True
    except ValueError:
        return None, False
