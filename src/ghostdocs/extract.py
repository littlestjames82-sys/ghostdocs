"""Text extraction for MD / TXT / HTML / PDF (text layer only).

Stdlib only. Honesty rules from PLAN.md:
- DOCX (and other office formats) are NOT covered, never silently skipped.
- Image-only / no-text PDFs are NOT covered and land on the not-covered list.
- Every PDF carries extraction-quality data (pages, chars, chars/page, flags)
  so a low-yield extraction looks low-yield instead of pretending it worked.
"""
from __future__ import annotations

import re
import zlib
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

COVERED_EXTS = {".md", ".markdown", ".txt", ".text", ".html", ".htm", ".pdf"}
NOT_COVERED_EXTS = {
    ".docx": "DOCX not covered in v0.1 (no stdlib DOCX text extraction adopted)",
    ".doc": "legacy Word .doc not covered in v0.1",
    ".odt": "ODT not covered in v0.1",
    ".xlsx": "spreadsheets not covered in v0.1",
    ".xls": "spreadsheets not covered in v0.1",
    ".pptx": "slides not covered in v0.1",
    ".ppt": "slides not covered in v0.1",
    ".rtf": "RTF not covered in v0.1",
}

LOW_YIELD_CHARS_PER_PAGE = 50


@dataclass
class Extraction:
    text: str = ""
    fmt: str = ""
    covered: bool = False
    reason: str = ""              # why not covered, when covered is False
    pages: int | None = None      # PDFs only
    chars: int = 0
    chars_per_page: float | None = None
    flags: list[str] = field(default_factory=list)


class _HTMLText(HTMLParser):
    """Extract text + heading levels, dropping script/style content."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0
        self.headings: list[tuple[int, str]] = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._skip += 1
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "tr", "br", "div"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self._skip:
            self._skip -= 1
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(tag[1])
            # the last non-empty part chunk is the heading text
            self.parts.append(f"\n{'#' * level} ")

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def _decode_text_bytes(raw: bytes) -> tuple[str, bool]:
    for enc in ("utf-8", "utf-16"):
        try:
            return raw.decode(enc), False
        except (UnicodeDecodeError, UnicodeError):
            continue
    return raw.decode("latin-1"), True


def extract_html(raw: bytes) -> Extraction:
    text, lossy = _decode_text_bytes(raw)
    parser = _HTMLText()
    try:
        parser.feed(text)
    except Exception:
        pass
    out = "".join(parser.parts)
    out = re.sub(r"[ \t]+", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    flags = ["lossy-decode"] if lossy else []
    return Extraction(text=out, fmt="html", covered=bool(out), chars=len(out),
                      reason="" if out else "HTML contained no extractable text",
                      flags=flags)


# ---------------- PDF (text layer only) ----------------

def _pdf_streams(data: bytes):
    """Yield decompressed (or raw) stream payloads."""
    pos = 0
    while True:
        start = data.find(b"stream", pos)
        if start == -1:
            return
        start += len(b"stream")
        if data[start:start + 2] == b"\r\n":
            start += 2
        elif data[start:start + 1] in (b"\n", b"\r"):
            start += 1
        end = data.find(b"endstream", start)
        if end == -1:
            return
        payload = data[start:end].rstrip(b"\r\n")
        header = data[max(0, start - 400):start]
        if b"FlateDecode" in header:
            try:
                payload = zlib.decompress(payload)
            except zlib.error:
                try:
                    payload = zlib.decompressobj().decompress(payload)
                except zlib.error:
                    payload = b""
        yield payload
        pos = end + len(b"endstream")


def _pdf_literal_strings(content: bytes) -> list[str]:
    """Pull ( ... ) Tj / TJ string operands from a content stream."""
    out: list[str] = []
    i, n = 0, len(content)
    while i < n:
        if content[i:i + 1] == b"(":
            depth, j, buf = 1, i + 1, bytearray()
            while j < n and depth:
                c = content[j]
                if c == 0x5C and j + 1 < n:  # backslash escape
                    nxt = content[j + 1]
                    mapping = {ord("n"): "\n", ord("r"): "\r", ord("t"): "\t",
                               ord("("): "(", ord(")"): ")", ord("\\"): "\\"}
                    if nxt in mapping:
                        buf.extend(mapping[nxt].encode("latin-1")); j += 2; continue
                    if 48 <= nxt <= 55:  # octal, up to 3 digits
                        k = j + 1; oct_digits = b""
                        while k < n and len(oct_digits) < 3 and 48 <= content[k] <= 55:
                            oct_digits += bytes([content[k]]); k += 1
                        buf.append(int(oct_digits, 8) & 0xFF); j = k; continue
                    buf.append(nxt); j += 2; continue
                if c == ord("("):
                    depth += 1
                elif c == ord(")"):
                    depth -= 1
                    if depth == 0:
                        j += 1; break
                buf.append(c); j += 1
            out.append(buf.decode("latin-1"))
            i = j
        else:
            i += 1
    return out


def extract_pdf(raw: bytes) -> Extraction:
    pages = len(re.findall(rb"/Type\s*/Page(?![s\w])", raw))
    if pages == 0:
        counts = re.findall(rb"/Count\s+(\d+)", raw)
        if counts:
            pages = int(counts[0])
    lines: list[str] = []
    for payload in _pdf_streams(raw):
        if b"Tj" not in payload and b"TJ" not in payload and b"BT" not in payload:
            continue
        strings = _pdf_literal_strings(payload)
        if strings:
            lines.append(" ".join(s.strip() for s in strings if s.strip()))
    text = "\n".join(lines).strip()
    chars = len(text)
    cpp = (chars / pages) if pages else None
    flags: list[str] = []
    if cpp is not None and cpp < LOW_YIELD_CHARS_PER_PAGE:
        flags.append("low-yield")
    if pages == 0:
        flags.append("page-count-unknown")
    if not text:
        return Extraction(text="", fmt="pdf", covered=False, pages=pages,
                          chars=0, chars_per_page=cpp, flags=flags + ["no-text-layer"],
                          reason="PDF has no extractable text layer (image-only or scanned PDFs are not covered in v0.1, no OCR)")
    if cpp is not None and cpp < 5:
        return Extraction(text=text, fmt="pdf", covered=False, pages=pages,
                          chars=chars, chars_per_page=cpp, flags=flags + ["near-empty-text-layer"],
                          reason="PDF text layer is near-empty; treated as not covered rather than pretending extraction worked")
    return Extraction(text=text, fmt="pdf", covered=True, pages=pages,
                      chars=chars, chars_per_page=cpp, flags=flags)


def extract_file(path: Path) -> Extraction:
    ext = path.suffix.lower()
    if ext in NOT_COVERED_EXTS:
        return Extraction(fmt=ext.lstrip("."), covered=False, reason=NOT_COVERED_EXTS[ext])
    raw = path.read_bytes()
    if ext == ".pdf":
        return extract_pdf(raw)
    if ext in (".html", ".htm"):
        return extract_html(raw)
    if ext in (".md", ".markdown", ".txt", ".text"):
        text, lossy = _decode_text_bytes(raw)
        fmt = "markdown" if ext in (".md", ".markdown") else "text"
        flags = ["lossy-decode"] if lossy else []
        text = text.strip()
        return Extraction(text=text, fmt=fmt, covered=True, chars=len(text),
                          flags=flags, reason="")
    return Extraction(fmt=ext.lstrip("."), covered=False,
                      reason=f"format {ext} not covered in v0.1")
