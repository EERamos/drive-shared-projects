"""Validate 01_INDEX against the files on disk. The exit code is the verdict.

Usage:
    python scripts/check_index.py --root ./my-project [--max-chars 50000]

Findings:
    MISSING_ROW      a file under 10_context or 20_sources has no index row
    STALE_ROW        an index row points to a file that does not exist
    TOO_LARGE        a file in 10_context exceeds --max-chars characters
    DUPLICATE_TOPIC  a 10_context file shares its topic with a 20_sources file
                     and has no "Source:" line pointing back to it
Exit codes: 0 clean, 1 findings, 2 usage error.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

from build_index import scan_files
from common import (
    CONTEXT_DIR,
    DEFAULT_MAX_CHARS,
    INDEX_FILE,
    SOURCES_DIR,
    normalize_stem,
    parse_index,
    read_text,
)

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2


class FindingKind(Enum):
    MISSING_ROW = auto()
    STALE_ROW = auto()
    TOO_LARGE = auto()
    DUPLICATE_TOPIC = auto()


@dataclass(frozen=True)
class Finding:
    kind: FindingKind
    path: str
    detail: str

    def __str__(self) -> str:
        return f"{self.kind.name} {self.path}: {self.detail}"


def _has_source_line(text: str) -> bool:
    return any(line.strip().lower().startswith("source:") for line in text.splitlines())


def _context_files(files: Sequence[str]) -> list[str]:
    return [f for f in files if f.startswith(CONTEXT_DIR + "/")]


def _source_files(files: Sequence[str]) -> list[str]:
    return [f for f in files if f.startswith(SOURCES_DIR + "/")]


def check(root: Path, max_chars: int = DEFAULT_MAX_CHARS) -> list[Finding]:
    """Return every inconsistency between the index and the folder, in a stable order."""
    findings: list[Finding] = []
    files = scan_files(root)
    indexed = [row.file for row in parse_index(read_text(root / INDEX_FILE))]
    on_disk = set(files)

    for rel in files:
        if rel not in indexed:
            findings.append(Finding(FindingKind.MISSING_ROW, rel, "file has no index row"))
    for rel in indexed:
        if rel not in on_disk:
            findings.append(Finding(FindingKind.STALE_ROW, rel, "row exists but file is missing"))

    sources_by_topic: dict[str, list[str]] = {}
    for rel in _source_files(files):
        sources_by_topic.setdefault(normalize_stem(rel), []).append(rel)

    for rel in _context_files(files):
        path = root / rel
        if path.suffix.lower() not in {".md", ".txt"}:
            continue
        text = read_text(path)
        if len(text) > max_chars:
            findings.append(
                Finding(FindingKind.TOO_LARGE, rel, f"{len(text)} chars, limit {max_chars}")
            )
        twins = sources_by_topic.get(normalize_stem(rel), [])
        if twins and not _has_source_line(text):
            findings.append(
                Finding(
                    FindingKind.DUPLICATE_TOPIC,
                    rel,
                    "same topic as " + ", ".join(twins) + " but no 'Source:' line",
                )
            )
    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate 01_INDEX against the folder.")
    parser.add_argument("--root", required=True, type=Path, help="Project folder.")
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return EXIT_USAGE if exc.code else EXIT_OK
    root: Path = args.root
    if not (root / INDEX_FILE).is_file():
        print(f"error: {root / INDEX_FILE} not found", file=sys.stderr)
        return EXIT_USAGE
    findings = check(root, max_chars=args.max_chars)
    if not findings:
        print("OK: index and folder are consistent")
        return EXIT_OK
    for finding in findings:
        print(finding)
    print(f"{len(findings)} finding(s)")
    return EXIT_FINDINGS


if __name__ == "__main__":
    sys.exit(main())
