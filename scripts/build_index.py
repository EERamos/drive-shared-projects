"""Scan a project tree and print or refresh the 01_INDEX table.

Usage:
    python scripts/build_index.py --root ./my-project           # print the table
    python scripts/build_index.py --root ./my-project --write   # rewrite the table in 01_INDEX.md

Rows already in the index keep their Drive ID, summary, "when to read" and owner.
Files that disappeared lose their row; with --write the dropped rows are listed on stderr
so the deletion is never silent. New files get TODO-ID and the first heading as summary;
a file that is not UTF-8 text gets an empty summary instead of raising.
Exit codes: 0 ok, 2 usage error (01_INDEX.md, 10_context or 20_sources missing).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from common import (
    ID_PLACEHOLDER,
    INDEX_FILE,
    SCANNED_DIRS,
    TEXT_SUFFIXES,
    ExitCode,
    IndexRow,
    first_heading,
    parse_args_or_exit,
    parse_index,
    read_text,
    render_index_table,
    replace_index_table,
    scan_files,
    write_text,
)

EXIT_OK = ExitCode.OK
EXIT_USAGE = ExitCode.USAGE


def _summary_for(root: Path, rel: str) -> str:
    path = root / rel
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return ""
    try:
        text = read_text(path)
    except (UnicodeDecodeError, OSError):
        return ""
    return first_heading(text) or ""


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


def dropped_rows(existing: Sequence[IndexRow], scanned: Sequence[IndexRow]) -> list[str]:
    """Files listed in the index that the scan did not find, in index order, without repeats."""
    kept = {row.file for row in scanned}
    return [file for file in dict.fromkeys(row.file for row in existing) if file not in kept]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Print or refresh the 01_INDEX table.")
    parser.add_argument("--root", required=True, type=Path, help="Project folder.")
    parser.add_argument("--write", action="store_true", help="Rewrite the table in 01_INDEX.md.")
    return parser


def _missing_paths(root: Path) -> list[Path]:
    """Required paths that are absent, so --write never rewrites the index from half a tree."""
    missing: list[Path] = []
    index_path = root / INDEX_FILE
    if not index_path.is_file():
        missing.append(index_path)
    missing.extend(root / sub for sub in SCANNED_DIRS if not (root / sub).is_dir())
    return missing


def main(argv: Sequence[str] | None = None) -> int:
    parsed = parse_args_or_exit(build_parser(), argv)
    if isinstance(parsed, int):
        return parsed
    args = parsed
    root: Path = args.root
    missing = _missing_paths(root)
    if missing:
        for path in missing:
            print(f"error: {path} not found", file=sys.stderr)
        return EXIT_USAGE
    index_path = root / INDEX_FILE
    index_text = read_text(index_path)
    existing = parse_index(index_text)
    scanned = scan(root)
    table = render_index_table(merge(existing, scanned))
    if args.write:
        dropped = dropped_rows(existing, scanned)
        if dropped:
            print(
                f"removed {len(dropped)} stale row(s): {', '.join(dropped)}",
                file=sys.stderr,
            )
        write_text(index_path, replace_index_table(index_text, table))
        print(f"updated {index_path}")
    else:
        print(table, end="")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
