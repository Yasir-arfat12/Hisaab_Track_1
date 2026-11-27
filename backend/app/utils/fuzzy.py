import re

from rapidfuzz import fuzz

_SUFFIX_RE = re.compile(r"\b(pvt|ltd|limited|india|private|inc|llc|services)\b", re.IGNORECASE)


def normalize_merchant_name(name: str) -> str:
    """Normalize merchant name for deduplication and fuzzy matching."""
    cleaned = _SUFFIX_RE.sub("", name.lower())
    cleaned = re.sub(r"[^a-z0-9\s]", " ", cleaned)
    return " ".join(cleaned.split())


def merchant_match_score(narration: str, merchant_name: str) -> float:
    """Compute fuzzy match score (0.0 - 100.0) between bank narration and merchant name."""
    norm_narration = normalize_merchant_name(narration)
    norm_merchant = normalize_merchant_name(merchant_name)
    if not norm_narration or not norm_merchant:
        return 0.0
    return float(fuzz.token_set_ratio(norm_narration, norm_merchant))
