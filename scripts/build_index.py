"""Scan a project tree and print or refresh the 01_INDEX table.

Usage:
    python scripts/build_index.py --root ./my-project
    python scripts/build_index.py --root ./my-project --write
    python scripts/build_index.py --root ./my-project --write --allow-drop

Rows already in the index keep their human-maintained fields. Vault frontmatter can
supply a stable Drive ID, title and owner, which also lets a renamed file inherit the
old row by Drive ID. A write that would remove stale rows is refused unless
`--allow-drop` is present. `Last updated` is refreshed on every successful write.

Exit codes: 0 done, 1 refused, 2 usage error. Exit 2 covers a missing project path
(00_INSTRUCTIONS.md, 01_INDEX.md, 90_LOG.md, 10_context or 20_sources) and an index
that is not UTF-8 text.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from common import (
    ID_PLACEHOLDER,
    INDEX_FILE,
    TEXT_SUFFIXES,
    ExitCode,
    IndexRow,
    first_heading,
    is_real_drive_id,
    missing_project_paths,
    parse_args_or_exit,
    parse_frontmatter,
    parse_index,
    read_index_or_error,
    read_text,
    refresh_last_updated,
    render_index_table,
    replace_index_table,
    scan_files,
    write_text,
)

EXIT_OK = ExitCode.OK
EXIT_REFUSED = ExitCode.REFUSED
EXIT_USAGE = ExitCode.USAGE


def _metadata_for(root: Path, rel: str) -> tuple[str, str, str]:
    """Return `(drive_id, summary, owner)` inferred from a local text file."""
    path = root / rel
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return ID_PLACEHOLDER, "", ""
    try:
        text = read_text(path)
    except (UnicodeDecodeError, OSError):
        return ID_PLACEHOLDER, "", ""
    metadata = parse_frontmatter(text)
    drive_id = metadata.get("drive_id", "").strip() or ID_PLACEHOLDER
    summary = metadata.get("title", "").strip() or first_heading(text) or ""
    owner = metadata.get("owner", "").strip()
    return drive_id, summary, owner


def scan(root: Path) -> list[IndexRow]:
    """Fresh rows for every file on disk, using frontmatter when available."""
    rows: list[IndexRow] = []
    for rel in scan_files(root):
        drive_id, summary, owner = _metadata_for(root, rel)
        rows.append(IndexRow(rel, drive_id, summary, "", owner))
    return rows


def duplicate_files(existing: Sequence[IndexRow]) -> list[str]:
    """Files that `existing` lists more than once, in first-seen order."""
    counts = Counter(row.file for row in existing)
    return [file for file in dict.fromkeys(row.file for row in existing) if counts[file] > 1]


def _rows_by_unique_id(rows: Sequence[IndexRow]) -> dict[str, IndexRow]:
    counts = Counter(row.drive_id for row in rows if is_real_drive_id(row.drive_id))
    return {
        row.drive_id: row
        for row in rows
        if is_real_drive_id(row.drive_id) and counts[row.drive_id] == 1
    }


def merge(existing: Sequence[IndexRow], scanned: Sequence[IndexRow]) -> list[IndexRow]:
    """Merge disk state with the human-maintained index.

    Exact path wins. If the path changed, a unique real Drive ID in frontmatter can
    reconnect the renamed file to its previous row so summary/reading rule/owner survive.
    """
    by_file: dict[str, IndexRow] = {}
    for row in existing:
        by_file.setdefault(row.file, row)
    by_id = _rows_by_unique_id(existing)

    merged: list[IndexRow] = []
    for fresh in scanned:
        old = by_file.get(fresh.file)
        if old is None and is_real_drive_id(fresh.drive_id):
            old = by_id.get(fresh.drive_id)
        if old is None:
            merged.append(fresh)
            continue
        drive_id = fresh.drive_id if is_real_drive_id(fresh.drive_id) else old.drive_id
        if not is_real_drive_id(drive_id):
            drive_id = fresh.drive_id or ID_PLACEHOLDER
        merged.append(
            IndexRow(
                file=fresh.file,
                drive_id=drive_id,
                summary=old.summary or fresh.summary,
                when_to_read=old.when_to_read,
                owner=old.owner or fresh.owner,
            )
        )
    return merged


def dropped_rows(existing: Sequence[IndexRow], scanned: Sequence[IndexRow]) -> list[str]:
    """Rows no longer represented by path or by a stable Drive ID."""
    scanned_files = {row.file for row in scanned}
    scanned_ids = {row.drive_id for row in scanned if is_real_drive_id(row.drive_id)}
    dropped: list[str] = []
    for row in existing:
        retained = row.file in scanned_files or (
            is_real_drive_id(row.drive_id) and row.drive_id in scanned_ids
        )
        if not retained and row.file not in dropped:
            dropped.append(row.file)
    return dropped


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Print or refresh the 01_INDEX table.")
    parser.add_argument("--root", required=True, type=Path, help="Project folder.")
    parser.add_argument("--write", action="store_true", help="Rewrite the table in 01_INDEX.md.")
    parser.add_argument(
        "--allow-drop",
        action="store_true",
        help="Allow --write to remove stale rows. Without it, destructive writes are refused.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parsed = parse_args_or_exit(build_parser(), argv)
    if isinstance(parsed, int):
        return parsed
    args = parsed
    root: Path = args.root
    missing = missing_project_paths(root)
    if missing:
        for path in missing:
            print(f"error: {path} not found", file=sys.stderr)
        return EXIT_USAGE
    index_path = root / INDEX_FILE
    index_text = read_index_or_error(index_path)
    if isinstance(index_text, int):
        return index_text
    existing = parse_index(index_text)
    for file in duplicate_files(existing):
        print(f"warning: duplicate index rows for {file} (kept the first)", file=sys.stderr)
    scanned = scan(root)
    dropped = dropped_rows(existing, scanned)
    table = render_index_table(merge(existing, scanned))
    if args.write:
        if dropped and not args.allow_drop:
            print(
                "refused: write would remove stale row(s): " + ", ".join(dropped),
                file=sys.stderr,
            )
            print("rerun with --allow-drop after reviewing them", file=sys.stderr)
            return EXIT_REFUSED
        if dropped:
            print(
                f"removed {len(dropped)} stale row(s): {', '.join(dropped)}",
                file=sys.stderr,
            )
        refreshed = refresh_last_updated(index_text, dt.date.today().isoformat())
        write_text(index_path, replace_index_table(refreshed, table))
        print(f"updated {index_path}")
    else:
        print(table, end="")
        if dropped:
            print(
                "would remove stale row(s) on write: " + ", ".join(dropped),
                file=sys.stderr,
            )
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
