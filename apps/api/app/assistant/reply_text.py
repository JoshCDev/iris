"""Strip markdown and unusable source tags from assistant replies."""
from __future__ import annotations

import re

_SOURCE = re.compile(r"\[(?:Source|Sumber):[^\]]*\]", re.IGNORECASE)
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_UNDER = re.compile(r"__(.+?)__")
_CODE = re.compile(r"`([^`]+)`")
_HEADING = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_BULLET = re.compile(r"^\s*[-*•]\s+", re.MULTILINE)


_ONNX_TRIAGE = re.compile(r"(?i)\b(?:the\s+)?ONNX\s+triage\b")
_ONNX = re.compile(r"(?i)\bONNX\b")


def plain_reply(text: str) -> str:
    s = (text or "").replace("\r\n", "\n")
    s = _SOURCE.sub("", s)
    s = _BOLD.sub(r"\1", s)
    s = _UNDER.sub(r"\1", s)
    s = _CODE.sub(r"\1", s)
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    s = _HEADING.sub("", s)
    s = _BULLET.sub("", s)
    s = s.replace("**", "")
    s = _ONNX_TRIAGE.sub("the photo check", s)
    s = _ONNX.sub("", s)
    s = re.sub(r"[ \t]+\n", "\n", s)
    s = re.sub(r" {2,}", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()
