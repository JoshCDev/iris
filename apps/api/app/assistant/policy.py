"""Deterministic reply-safety checks (no LLM involved)."""
from __future__ import annotations

import re

_PESTICIDE_DOSE = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(ml|g|kg|cc|liter|litre|L)\b.{0,40}"
    r"(per\s*(ha|liter|litre)|dosis|takaran)", re.IGNORECASE)
_UNSUPPORTED_CERTAINTY = re.compile(
    r"(pasti\s*(sembuh|berhasil)|100%\s*(sembuh|pulih|cure)|guaranteed\s*cure)",
    re.IGNORECASE)

_REFUSAL = (
    "IRIS does not provide pesticide doses or guaranteed outcomes. "
    "Consult an extension officer for treatment decisions."
)


def check_reply_safety(reply: str) -> str | None:
    """Return a safe replacement when the reply violates policy."""
    if not reply:
        return None
    if _PESTICIDE_DOSE.search(reply) or _UNSUPPORTED_CERTAINTY.search(reply):
        return _REFUSAL
    return None
