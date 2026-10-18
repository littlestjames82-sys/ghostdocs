"""Corpus profile: .ghostdocs.json in the corpus folder."""
from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass, field
from pathlib import Path

PROFILE_NAME = ".ghostdocs.json"


@dataclass
class Profile:
    include: list[str] = field(default_factory=list)          # globs, empty = all
    exclude: list[str] = field(default_factory=list)          # globs
    authoritative_sources: list[str] = field(default_factory=list)  # path prefixes/globs
    modes: dict[str, str] = field(default_factory=dict)       # glob -> full|headings|exclude
    superseded: str = "exclude"  # exclude (from exports, kept in reports) | include
    source_path: str | None = None

    def mode_for(self, rel: str) -> str:
        for glob, mode in self.modes.items():
            if fnmatch.fnmatch(rel, glob):
                return mode
        return "full"

    def is_authoritative(self, rel: str) -> bool:
        for pat in self.authoritative_sources:
            if fnmatch.fnmatch(rel, pat) or rel.startswith(pat.rstrip("/") + "/") or rel.startswith(pat):
                return True
        return False

    def included(self, rel: str) -> bool:
        if self.include and not any(fnmatch.fnmatch(rel, g) for g in self.include):
            return False
        if any(fnmatch.fnmatch(rel, g) for g in self.exclude):
            return False
        return self.mode_for(rel) != "exclude"


def load_profile(corpus: Path) -> Profile:
    p = corpus / PROFILE_NAME
    if not p.exists():
        return Profile()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid {PROFILE_NAME}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"invalid {PROFILE_NAME}: top level must be an object")
    known = {"include", "exclude", "authoritative_sources", "modes", "superseded"}
    unknown = set(data) - known
    if unknown:
        raise ValueError(f"invalid {PROFILE_NAME}: unknown keys {sorted(unknown)}")
    modes = data.get("modes", {}) or {}
    for mode in modes.values():
        if mode not in ("full", "headings", "exclude"):
            raise ValueError(f"invalid {PROFILE_NAME}: mode must be full|headings|exclude, got {mode!r}")
    superseded = data.get("superseded", "exclude")
    if superseded not in ("exclude", "include"):
        raise ValueError(f"invalid {PROFILE_NAME}: superseded must be exclude|include")
    return Profile(include=list(data.get("include", [])),
                   exclude=list(data.get("exclude", [])),
                   authoritative_sources=list(data.get("authoritative_sources", [])),
                   modes=dict(modes), superseded=superseded,
                   source_path=str(p))
