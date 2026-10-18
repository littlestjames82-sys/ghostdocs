"""Section model: chunk boundaries are document sections, never arbitrary splits."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

from .tokens import estimate_tokens

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_DATE_PATTERNS = [
    re.compile(r"\b(20\d{2})-(0[1-9]|1[0-2])-([0-3]\d)\b"),
    re.compile(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+([0-3]?\d),\s+(20\d{2})\b"),
]
_MONTHS = {m: i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"])}


def find_date(text: str) -> str | None:
    """First explicit ISO or 'Month D, YYYY' date in the text, normalised to ISO."""
    for pat in _DATE_PATTERNS:
        m = pat.search(text)
        if m:
            if pat is _DATE_PATTERNS[0]:
                return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
            month = _MONTHS[m.group(1)]
            return f"{m.group(3)}-{month:02d}-{int(m.group(2)):02d}"
    return None


@dataclass
class Section:
    doc_path: str
    index: int
    title: str
    heading_trail: list[str] = field(default_factory=list)
    text: str = ""

    @property
    def tokens(self) -> int:
        return estimate_tokens(self.text)

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()


def split_sections(doc_path: str, text: str) -> list[Section]:
    """Split on Markdown-style headings; heading-less docs are one section."""
    sections: list[Section] = []
    trail: list[str] = []
    cur_title = Path_title(doc_path)
    cur_lines: list[str] = []

    def flush():
        body = "\n".join(cur_lines).strip()
        if body or not sections:
            sections.append(Section(doc_path=doc_path, index=len(sections),
                                    title=cur_title, heading_trail=list(trail),
                                    text=body))

    for line in text.splitlines():
        m = _HEADING.match(line)
        if m:
            flush()
            level = len(m.group(1))
            cur_title = m.group(2).strip()
            trail = trail[:level - 1] + [cur_title]
            cur_lines = [line]
        else:
            cur_lines.append(line)
    flush()
    return [s for s in sections if s.text] or sections


def Path_title(doc_path: str) -> str:
    name = doc_path.rsplit("/", 1)[-1]
    return name.rsplit(".", 1)[0].replace("-", " ").replace("_", " ")


def first_paragraph(text: str) -> str:
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if block and not block.startswith("#"):
            return block
    lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
    return lines[0] if lines else ""


def headings_render(section: Section) -> str:
    """Headings mode: heading trail + first paragraph only."""
    parts = []
    for i, h in enumerate(section.heading_trail or [section.title]):
        parts.append(f"{'#' * (i + 1)} {h}")
    para = first_paragraph(section.text)
    if para:
        parts.append(para)
    return "\n\n".join(parts)
