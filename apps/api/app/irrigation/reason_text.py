"""Map stored scheduler sentences (ID or EN) to English for API clients."""
from __future__ import annotations

import re

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"^Kondisi aman \((.+); pemicu (.+)\)\. "
            r"Pantau(?: kembali dalam)? 15 menit(?: berikutnya)?\.$"
        ),
        r"Safe (\1; trigger \2). Check again in 15 minutes.",
    ),
    (
        re.compile(r"^Menunggu hujan: prakiraan (.+) mm dalam 72 jam\.$"),
        r"Holding for rain: \1 mm forecast in 72 h.",
    ),
    (
        re.compile(
            r"^Fase pembungaan: sawah wajib tergenang \(≥ \+3 cm\) "
            r"agar hasil tidak turun\.$"
        ),
        r"Flowering lock: keep the field flooded (≥ +3 cm) to protect yield.",
    ),
    (
        re.compile(
            r"^Ambang safe-AWD tercapai \((.+) cm\)\. Irigasi hingga \+(.+) cm\.$"
        ),
        r"Safe-AWD trigger reached (\1 cm). Irrigate to +\2 cm.",
    ),
    (
        re.compile(
            r"^Musim tanam selesai: sawah dapat ditiriskan untuk panen\.$"
        ),
        r"Season complete: the field can be drained for harvest.",
    ),
]


def english_reason(reason: str | None) -> str | None:
    if not reason:
        return reason
    for pat, repl in _PATTERNS:
        if pat.search(reason):
            return pat.sub(repl, reason)
    return reason
