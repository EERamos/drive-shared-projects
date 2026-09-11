"""Scan a project tree and print or refresh the 01_INDEX table.

Usage:
    python scripts/build_index.py --root ./my-project           # print the table
    python scripts/build_index.py --root ./my-project --write   # rewrite the table in 01_INDEX.md

Rows already in the index keep their Drive ID, summary, "when to read" and owner.
Files that disappeared lose their row. New files get TODO-ID and the first heading as summary.
Exit codes: 0 ok, 2 usage error (root or 01_INDEX.md missing).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from common import (
    CONTEXT_DIR,
    ID_PLACEHOLDER,
    INDEX_FILE,
    SOURCES_DIR,
    IndexRow,
    first_heading,
    parse_index,
    read_text,
    relative_posix,
    render_index_table,
    replace_index_table,
    write_text,
)

EXIT_OK = 0
EXIT_USAGE = 2

_SCANNED_DIRS = (CONTEXT_DIR, SOURCES_DIR)
_TEXT_SUFFIXES = {".md", ".txt"}


def scan_files(root: Path) -> list[str]:
    """Relative POSIX paths of every non-dot file under 10_context and 20_sources, sorted."""
    found: list[str] = []
    for sub in _SCANNED_DIRS:
        base = root / sub
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if path.is_file() and not path.name.startswith("."):
                found.append(relative_posix(root, path))
    return sorted(found)


def _summary_for(root: Path, rel: str) -> str:
    path = root / rel
    if path.suffix.lower() not in _TEXT_SUFFIXES:
        return ""
    return first_heading(read_text(path)) or ""


def scan(root: Path) -> list[IndexRow]:
    """Fresh rows for every file on disk, with placeholders where a human must fill in."""
    return [
        IndexRow(rel, ID_PLACEHOLDER, _summary_for(root, rel), "", "") for rel in scan_files(root)
    ]


def merge(existing: Sequence[IndexRow], scanned: Sequence[IndexRow]) -> list[IndexRow]:
    """Keep human-entered fields from `existing`; order and membership follow `scanned`."""
    by_file = {row.file: row for row in existing}
    merged: list[IndexRow] = []
    for fresh in scanned:
        old = by_file.get(fresh.file)
        if old is None:
            merged.append(fresh)
            continue
        merged.append(
            IndexRow(
                file=fresh.file,
                drive_id=old.drive_id or fresh.drive_id,
                summary=old.summary or fresh.summary,
                when_to_read=old.when_to_read,
                owner=old.owner,
            )
        )
    return merged


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Print or refresh the 01_INDEX table.")
    parser.add_argument("--root", required=True, type=Path, help="Project folder.")
    parser.add_argument("--write", action="store_true", help="Rewrite the table in 01_INDEX.md.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return EXIT_USAGE if exc.code else EXIT_OK
    root: Path = args.root
    index_path = root / INDEX_FILE
    if not index_path.is_file():
        print(f"error: {index_path} not found", file=sys.stderr)
        return EXIT_USAGE
    index_text = read_text(index_path)
    table = render_index_table(merge(parse_index(index_text), scan(root)))
    if args.write:
        write_text(index_path, replace_index_table(index_text, table))
        print(f"updated {index_path}")
    else:
        print(table, end="")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
