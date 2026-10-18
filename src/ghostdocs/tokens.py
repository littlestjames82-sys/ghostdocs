"""Token estimation. Estimates only, never billed counts."""
from __future__ import annotations
import re

_WORD = re.compile(r"[a-z0-9]+")

def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, round(len(text) / 4))

def words(text: str) -> list[str]:
    return _WORD.findall(text.lower())
