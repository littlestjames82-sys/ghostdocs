"""GhostDocs CLI: scan / export / report / check."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from . import __version__
from .export import export_corpus
from .profile import load_profile
from .report import write_report
from .scan import scan_corpus


def _load(args):
    corpus_path = Path(args.corpus)
    if not corpus_path.is_dir():
        print(f"error: corpus folder not found: {corpus_path}", file=sys.stderr)
        raise SystemExit(2)
    try:
        profile = load_profile(corpus_path)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
    return scan_corpus(corpus_path, profile)


def cmd_scan(args) -> int:
    corpus = _load(args)
    data = corpus.to_dict()
    if args.json:
        print(json.dumps(data, indent=2))
        return 0
    s = data["summary"]
    print(f"Documents: {s['documents']}  Not covered: {s['coverage_gaps']}  "
          f"Held out: {s['held_out_documents']}")
    print(f"Estimated tokens (raw): {s['total_estimated_tokens']}  "
          f"duplicate waste: {s['wasted_estimated_tokens']}  "
          f"deduped: {s['deduped_estimated_tokens']}")
    print("\nHeat (largest first):")
    for d in data["documents"][:args.top]:
        print(f"  {d['tokens']:>8}  {d['heat_pct']:>5}%  {d['path']}"
              + ("  HELD OUT" if d["held_out"] else "")
              + (f"  flags={','.join(d['extraction_flags'])}" if d["extraction_flags"] else ""))
    if corpus.clusters:
        print("\nDuplicate clusters:")
        for c in corpus.clusters:
            print(f"  [{c.kind}] current={c.probable_current} ({c.current_reason}) "
                  f"stale={c.stale} waste={c.wasted_tokens}")
            for m in c.members:
                print(f"    - {m}")
    if corpus.not_covered:
        print("\nNot covered (named, never silently skipped):")
        for n in corpus.not_covered:
            print(f"  - {n.path}: {n.reason}")
    return 0


def cmd_export(args) -> int:
    corpus = _load(args)
    result = export_corpus(corpus, Path(args.out), task=args.task, fit=args.fit,
                           shape=args.shape, allow_sensitive=args.allow_sensitive)
    print(f"Exported {result.sections_exported} sections to {result.out}")
    print(f"Exported estimated tokens: {result.total_tokens} "
          f"(corpus raw: {result.raw_tokens})")
    if result.held_out:
        print(f"Held out (sensitive): {', '.join(result.held_out)}")
    if result.superseded_skipped:
        print(f"Superseded skipped: {', '.join(result.superseded_skipped)}")
    if result.not_covered:
        print(f"Not covered: {', '.join(result.not_covered)}")
    if args.fit is not None and not result.fitted:
        print(f"WARNING: could not fit under {args.fit} tokens; bundle written anyway.",
              file=sys.stderr)
        return 1
    return 0


def cmd_report(args) -> int:
    corpus = _load(args)
    out = write_report(corpus, Path(args.out))
    print(f"Report written: {out}")
    return 0


def cmd_check(args) -> int:
    bundle = Path(args.bundle)
    manifest_path = bundle / "manifest.json"
    if not manifest_path.exists():
        print("error: no manifest.json in bundle", file=sys.stderr)
        return 2
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors = []
    for f in manifest.get("files", []):
        target = bundle / "files" / (f["path"] + ".txt")
        if not target.exists():
            chunks = bundle / "chunks.jsonl"
            if not chunks.exists():
                errors.append(f"missing exported file for {f['path']}")
            continue
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        if digest != f["sha256"]:
            errors.append(f"hash mismatch for {f['path']}")
    chunk_path = bundle / "chunks.jsonl"
    if chunk_path.exists():
        chunk_total = 0
        for line in chunk_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                chunk_total += json.loads(line)["estimated_tokens"]
        if chunk_total != manifest["totals"]["chunk_estimated_tokens"]:
            errors.append("chunk totals do not equal manifest chunk total")
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        return 1
    print("Bundle OK: hashes and totals match manifest.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="ghostdocs", description=__doc__)
    parser.add_argument("--version", action="version", version=f"ghostdocs {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("scan", help="scan a corpus folder")
    p.add_argument("corpus")
    p.add_argument("--json", action="store_true")
    p.add_argument("--top", type=int, default=20)
    p.set_defaults(fn=cmd_scan)

    p = sub.add_parser("export", help="export an agent bundle and/or chunk pack")
    p.add_argument("corpus")
    p.add_argument("-o", "--out", required=True)
    p.add_argument("--task", default=None)
    p.add_argument("--fit", type=int, default=None)
    p.add_argument("--shape", choices=["bundle", "chunks", "both"], default="both")
    p.add_argument("--allow-sensitive", action="store_true",
                   help="include sensitive-held documents (explicit opt-in, recorded)")
    p.set_defaults(fn=cmd_export)

    p = sub.add_parser("report", help="write a single-file HTML corpus report")
    p.add_argument("corpus")
    p.add_argument("-o", "--out", required=True)
    p.set_defaults(fn=cmd_report)

    p = sub.add_parser("check", help="validate an exported bundle against its manifest")
    p.add_argument("bundle")
    p.set_defaults(fn=cmd_check)

    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
