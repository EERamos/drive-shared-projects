"""Validate 01_INDEX against Google Drive listings saved from the connector.

Usage:
    python scripts/check_drive.py --instructions 00_INSTRUCTIONS.json --index 01_INDEX.json \
        --context-listing 10_context.json --sources-listing 20_sources.json \
        [--project-listing project.json]

The inputs are the tool results of the Drive connector saved verbatim: `read_file_content`
for the two documents and `search_files` with `parentId = '<folder id>'` for each listing.
Plain Markdown for the documents and a `path,drive_id` CSV for the listings are accepted too.

Every listing is bound to one folder. Both content listings are mandatory, so an empty
listing means an empty folder and a folder can never go unchecked. Every entry must belong
to the folder it was listed for: the same `parentId` recorded in 00_INSTRUCTIONS for JSON,
a path under that folder for CSV. Anything else is a usage error, not a finding.

Findings:
    MISSING_PROJECT_ID       canonical project ID absent/TODO-ID, or no Drive IDs section
    DUPLICATE_PROJECT_ID     a canonical project ID collides with another one or a row
    DUPLICATE_ROW            same path appears more than once in the index
    MISSING_DRIVE_ID         index row still has TODO-ID or an empty ID
    DUPLICATE_DRIVE_ID       one populated Drive ID is assigned to multiple rows
    NESTED_FOLDER            a folder inside 10_context or 20_sources; its contents are not checked
    DUPLICATE_TITLE          two Drive entries share the same path
    MISSING_CANONICAL_FILE   the project-root listing lacks one of the fixed entries
    DUPLICATE_CANONICAL_FILE both variants of a fixed entry exist (01_INDEX and 01_INDEX.md)
    UNEXPECTED_FILE          a project-root entry outside the fixed layout
    RENAMED_FILE             an index row's Drive ID now carries a different title
    MISSING_ROW              Drive file has no index row
    STALE_ROW                index row has no Drive file at that path
    ID_MISMATCH              index and Drive disagree on the ID of the same path

Exit codes: 0 clean, 1 findings, 2 usage error. Exit 2 covers an unreadable or malformed
input, a JSON document without fileContent, a listing whose folder has no ID recorded in
00_INSTRUCTIONS and a listing with entries that belong to another folder.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

from common import (
    CONTEXT_DIR,
    INSTRUCTIONS_FILE,
    SOURCES_DIR,
    DriveEntry,
    ExitCode,
    IndexRow,
    canonical_id_collisions,
    connector_markdown,
    duplicate_drive_id_paths,
    duplicate_row_counts,
    first_rows_by_file,
    instruction_drive_ids,
    is_real_drive_id,
    missing_canonical_ids,
    parse_args_or_exit,
    parse_index,
    parse_listing,
    read_text_or_error,
)

EXIT_OK = ExitCode.OK
EXIT_FINDINGS = ExitCode.FINDINGS
EXIT_USAGE = ExitCode.USAGE

_ROOT_FILES = ("00_INSTRUCTIONS", "01_INDEX", "90_LOG")
_ROOT_FOLDERS = (CONTEXT_DIR, SOURCES_DIR)
_ROOT_ID_LABELS = {
    "01_INDEX": "01_INDEX",
    "90_LOG": "90_LOG",
    CONTEXT_DIR: "10_context folder",
    SOURCES_DIR: "20_sources folder",
}
# Listing folder -> label of its ID in the Drive IDs section. "" is the project folder.
_LISTING_LABELS = {
    "": "Project folder",
    CONTEXT_DIR: "10_context folder",
    SOURCES_DIR: "20_sources folder",
}
_REQUIRED_LISTINGS = (CONTEXT_DIR, SOURCES_DIR)


class DriveFindingKind(Enum):
    MISSING_PROJECT_ID = auto()
    DUPLICATE_PROJECT_ID = auto()
    DUPLICATE_ROW = auto()
    MISSING_DRIVE_ID = auto()
    DUPLICATE_DRIVE_ID = auto()
    NESTED_FOLDER = auto()
    DUPLICATE_TITLE = auto()
    MISSING_CANONICAL_FILE = auto()
    DUPLICATE_CANONICAL_FILE = auto()
    UNEXPECTED_FILE = auto()
    RENAMED_FILE = auto()
    MISSING_ROW = auto()
    STALE_ROW = auto()
    ID_MISMATCH = auto()


@dataclass(frozen=True)
class DriveFinding:
    kind: DriveFindingKind
    path: str
    detail: str

    def __str__(self) -> str:
        return f"{self.kind.name} {self.path}: {self.detail}"


class ListingError(ValueError):
    """A listing cannot be used: missing, duplicated, unplaceable or holding foreign entries."""


@dataclass(frozen=True)
class Listing:
    """The saved listing of one project folder: "" for the project folder itself."""

    folder: str
    entries: tuple[DriveEntry, ...] = ()


@dataclass(frozen=True)
class _Placed:
    """A listing entry with the project path it resolves to."""

    path: str
    folder: str
    entry: DriveEntry


def _folder_name(folder: str) -> str:
    return folder or "the project folder"


def _listings_by_folder(listings: Sequence[Listing]) -> dict[str, Listing]:
    """Index the listings by folder; both content folders must be present exactly once."""
    by_folder: dict[str, Listing] = {}
    for listing in listings:
        if listing.folder not in _LISTING_LABELS:
            raise ListingError(f"unknown listing folder {listing.folder!r}")
        if listing.folder in by_folder:
            raise ListingError(f"{_folder_name(listing.folder)} is listed twice")
        by_folder[listing.folder] = listing
    for folder in _REQUIRED_LISTINGS:
        if folder not in by_folder:
            raise ListingError(
                f"{folder} listing is missing; both 10_context and 20_sources must be listed"
            )
    return by_folder


def _in_folder(path: str, folder: str) -> bool:
    """Whether a CSV path lies directly or deeper inside `folder` ("" is the project root)."""
    if not folder:
        return "/" not in path
    return path.startswith(folder + "/") and len(path) > len(folder) + 1


def _place(listing: Listing, instructions_text: str, project_ids: dict[str, str]) -> list[_Placed]:
    """Resolve every entry of one listing to a project path, or raise ListingError."""
    name = _folder_name(listing.folder)
    label = _LISTING_LABELS[listing.folder]
    expected = project_ids.get(label, "")
    if not is_real_drive_id(expected):
        reason = (
            f"{INSTRUCTIONS_FILE} has no Drive IDs section"
            if missing_canonical_ids(instructions_text) is None
            else f"{label} is empty or TODO-ID in {INSTRUCTIONS_FILE}"
        )
        raise ListingError(f"cannot check {name}: {reason}")
    placed: list[_Placed] = []
    foreign: list[str] = []
    for entry in listing.entries:
        if entry.path is not None:
            if _in_folder(entry.path, listing.folder):
                placed.append(_Placed(entry.path, listing.folder, entry))
            else:
                foreign.append(entry.path)
            continue
        if entry.parent_id is None:
            raise ListingError(
                f"{name} listing: entry {entry.title} ({entry.drive_id}) has no parentId"
            )
        if entry.parent_id != expected:
            foreign.append(f"{entry.title} (parent {entry.parent_id})")
            continue
        path = f"{listing.folder}/{entry.title}" if listing.folder else entry.title
        placed.append(_Placed(path, listing.folder, entry))
    if foreign:
        raise ListingError(
            f"{name} listing: entries outside {label} {expected}: " + ", ".join(foreign)
        )
    return placed


def _root_findings(root: dict[str, DriveEntry], project_ids: dict[str, str]) -> list[DriveFinding]:
    """Check the fixed layout of the project folder against the canonical IDs."""
    findings: list[DriveFinding] = []
    expected: set[str] = set()
    for name in (*_ROOT_FILES, *_ROOT_FOLDERS):
        candidates = [name, f"{name}.md"] if name in _ROOT_FILES else [name]
        expected.update(candidates)
        present = [candidate for candidate in candidates if candidate in root]
        if not present:
            findings.append(
                DriveFinding(
                    DriveFindingKind.MISSING_CANONICAL_FILE,
                    name,
                    "not found in the project folder listing",
                )
            )
            continue
        if len(present) > 1:
            variants = ", ".join(
                f"{candidate} ({root[candidate].drive_id})" for candidate in present
            )
            findings.append(
                DriveFinding(
                    DriveFindingKind.DUPLICATE_CANONICAL_FILE,
                    name,
                    f"both variants exist: {variants}; keep one",
                )
            )
            continue
        label = _ROOT_ID_LABELS.get(name)
        if label is None:
            continue
        recorded = project_ids.get(label, "")
        found = root[present[0]]
        if is_real_drive_id(recorded) and recorded != found.drive_id:
            findings.append(
                DriveFinding(
                    DriveFindingKind.ID_MISMATCH,
                    name,
                    f"{INSTRUCTIONS_FILE} records {recorded}, Drive lists {found.drive_id}",
                )
            )
    for path in sorted(root):
        if path not in expected:
            findings.append(
                DriveFinding(
                    DriveFindingKind.UNEXPECTED_FILE,
                    path,
                    "outside the fixed layout; move it into 20_sources or remove it",
                )
            )
    return findings


def _comparison_findings(
    rows_by_file: dict[str, IndexRow], drive_files: dict[str, DriveEntry]
) -> list[DriveFinding]:
    """Compare the index rows with the files Drive lists under 10_context and 20_sources."""
    findings: list[DriveFinding] = []
    row_files_by_id: dict[str, str] = {}
    for file, row in rows_by_file.items():
        if is_real_drive_id(row.drive_id):
            row_files_by_id.setdefault(row.drive_id, file)
    renamed: set[str] = set()
    for path in sorted(drive_files):
        if path in rows_by_file:
            continue
        entry = drive_files[path]
        old = row_files_by_id.get(entry.drive_id)
        if old is not None and old not in drive_files:
            findings.append(
                DriveFinding(
                    DriveFindingKind.RENAMED_FILE,
                    old,
                    f"Drive ID {entry.drive_id} is now titled {path}; update the File cell",
                )
            )
            renamed.add(old)
        else:
            findings.append(
                DriveFinding(DriveFindingKind.MISSING_ROW, path, "Drive file has no index row")
            )
    for file in sorted(rows_by_file):
        if file not in drive_files and file not in renamed:
            findings.append(
                DriveFinding(
                    DriveFindingKind.STALE_ROW,
                    file,
                    "row exists but Drive has no file at this path",
                )
            )
    for path in sorted(rows_by_file.keys() & drive_files.keys()):
        row = rows_by_file[path]
        entry = drive_files[path]
        if is_real_drive_id(row.drive_id) and row.drive_id != entry.drive_id:
            findings.append(
                DriveFinding(
                    DriveFindingKind.ID_MISMATCH,
                    path,
                    f"index ID {row.drive_id} != Drive ID {entry.drive_id}",
                )
            )
    return findings


def check_drive(
    instructions_text: str, index_text: str, listings: Sequence[Listing]
) -> list[DriveFinding]:
    """Return every inconsistency between the index and the Drive listings, in stable order.

    Both texts must already be normalized (see `common.connector_markdown`). The listings
    for 10_context and 20_sources are mandatory; the project folder one is optional. Raises
    ListingError when a listing is missing, duplicated, cannot be placed because its folder
    has no recorded ID, or holds entries of another folder.
    """
    by_folder = _listings_by_folder(listings)
    project_ids = instruction_drive_ids(instructions_text)
    placed: list[_Placed] = []
    for folder in _LISTING_LABELS:
        if folder in by_folder:
            placed.extend(_place(by_folder[folder], instructions_text, project_ids))

    findings: list[DriveFinding] = []
    rows = parse_index(index_text)
    missing = missing_canonical_ids(instructions_text)
    if missing is None:
        findings.append(
            DriveFinding(
                DriveFindingKind.MISSING_PROJECT_ID,
                INSTRUCTIONS_FILE,
                "Drive IDs section is missing",
            )
        )
    else:
        for label in missing:
            findings.append(
                DriveFinding(
                    DriveFindingKind.MISSING_PROJECT_ID,
                    INSTRUCTIONS_FILE,
                    f"{label} is empty or TODO-ID",
                )
            )
        for drive_id, locations in canonical_id_collisions(instructions_text, rows):
            findings.append(
                DriveFinding(
                    DriveFindingKind.DUPLICATE_PROJECT_ID,
                    INSTRUCTIONS_FILE,
                    f"Drive ID {drive_id} reused by " + ", ".join(locations),
                )
            )

    for path, count in duplicate_row_counts(rows):
        findings.append(DriveFinding(DriveFindingKind.DUPLICATE_ROW, path, f"listed {count} times"))
    for row in rows:
        if not is_real_drive_id(row.drive_id):
            findings.append(
                DriveFinding(
                    DriveFindingKind.MISSING_DRIVE_ID, row.file, "Drive ID is empty or TODO-ID"
                )
            )
    for drive_id, paths in duplicate_drive_id_paths(rows):
        findings.append(
            DriveFinding(
                DriveFindingKind.DUPLICATE_DRIVE_ID,
                paths[0],
                f"Drive ID {drive_id} also used by " + ", ".join(paths[1:]),
            )
        )

    for item in sorted(placed, key=lambda item: item.path):
        if item.folder and item.entry.is_folder:
            findings.append(
                DriveFinding(
                    DriveFindingKind.NESTED_FOLDER,
                    item.path,
                    f"folder inside {item.folder}; keep it flat, its contents are not checked",
                )
            )
    by_path: dict[str, list[DriveEntry]] = {}
    for item in placed:
        by_path.setdefault(item.path, []).append(item.entry)
    for path, listed in sorted(by_path.items()):
        if len(listed) > 1:
            findings.append(
                DriveFinding(
                    DriveFindingKind.DUPLICATE_TITLE,
                    path,
                    "several Drive entries share this title: "
                    + ", ".join(entry.drive_id for entry in listed),
                )
            )

    root: dict[str, DriveEntry] = {}
    drive_files: dict[str, DriveEntry] = {}
    for item in placed:
        if not item.folder:
            root.setdefault(item.path, item.entry)
        elif not item.entry.is_folder:
            drive_files.setdefault(item.path, item.entry)
    if "" in by_folder:
        findings.extend(_root_findings(root, project_ids))
    findings.extend(_comparison_findings(first_rows_by_file(rows), drive_files))
    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate 01_INDEX against Drive listings.")
    parser.add_argument(
        "--instructions",
        required=True,
        type=Path,
        help="Saved read of 00_INSTRUCTIONS: connector JSON or Markdown.",
    )
    parser.add_argument(
        "--index",
        required=True,
        type=Path,
        help="Saved read of 01_INDEX: connector JSON or Markdown.",
    )
    parser.add_argument(
        "--context-listing",
        required=True,
        type=Path,
        help="Saved search_files result for the 10_context folder, or a path,drive_id CSV of it.",
    )
    parser.add_argument(
        "--sources-listing",
        required=True,
        type=Path,
        help="Saved search_files result for the 20_sources folder, or a path,drive_id CSV of it.",
    )
    parser.add_argument(
        "--project-listing",
        type=Path,
        help="Optional saved listing of the project folder itself, to check the fixed layout.",
    )
    return parser


def _document(path: Path) -> str | int:
    """Read and normalize a saved document, or report why it cannot be used and return USAGE."""
    raw = read_text_or_error(path)
    if isinstance(raw, int):
        return raw
    try:
        return connector_markdown(raw)
    except ValueError as exc:
        print(f"error: {path}: {exc}", file=sys.stderr)
        return EXIT_USAGE


def _listing(folder: str, path: Path) -> Listing | int:
    """Read and parse one saved listing, or report why it cannot be used and return USAGE."""
    raw = read_text_or_error(path)
    if isinstance(raw, int):
        return raw
    try:
        return Listing(folder, tuple(parse_listing(raw)))
    except ValueError as exc:
        print(f"error: cannot read listing {path}: {exc}", file=sys.stderr)
        return EXIT_USAGE


def main(argv: Sequence[str] | None = None) -> int:
    parsed = parse_args_or_exit(build_parser(), argv)
    if isinstance(parsed, int):
        return parsed
    args = parsed
    instructions_text = _document(args.instructions)
    if isinstance(instructions_text, int):
        return instructions_text
    index_text = _document(args.index)
    if isinstance(index_text, int):
        return index_text
    listings: list[Listing] = []
    sources = (
        (CONTEXT_DIR, args.context_listing),
        (SOURCES_DIR, args.sources_listing),
        ("", args.project_listing),
    )
    for folder, path in sources:
        if path is None:
            continue
        listing = _listing(folder, path)
        if isinstance(listing, int):
            return listing
        listings.append(listing)
    try:
        findings = check_drive(instructions_text, index_text, listings)
    except ListingError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    if not findings:
        suffix = "" if args.project_listing else "; project folder not listed"
        print(f"OK: index and Drive listings are consistent{suffix}")
        return EXIT_OK
    for finding in findings:
        print(finding)
    print(f"{len(findings)} finding(s)")
    return EXIT_FINDINGS


if __name__ == "__main__":
    sys.exit(main())
