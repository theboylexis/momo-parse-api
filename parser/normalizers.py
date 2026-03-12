import re
from typing import Optional


def normalize_amount(value: str) -> Optional[float]:
    """Strip commas/whitespace and convert to float. Returns None on failure."""
    if value is None:
        return None
    cleaned = re.sub(r"[,\s]", "", str(value))
    try:
        return float(cleaned)
    except ValueError:
        return None


def normalize_phone(phone: str) -> Optional[str]:
    """Normalize Ghanaian phone numbers to +233XXXXXXXXX format."""
    if phone is None:
        return None
    cleaned = re.sub(r"[\s\-]", "", str(phone))
    if cleaned.startswith("0") and len(cleaned) == 10:
        return "+233" + cleaned[1:]
    if cleaned.startswith("233") and len(cleaned) == 12:
        return "+" + cleaned
    if cleaned.startswith("+233"):
        return cleaned
    return cleaned  # return as-is if format not recognized (e.g. agent codes like A25736)


def normalize_name(name: str) -> Optional[str]:
    """Strip trailing/leading whitespace from extracted names."""
    if name is None:
        return None
    return name.strip()
