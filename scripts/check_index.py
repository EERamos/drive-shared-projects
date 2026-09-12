"""Validate 01_INDEX against the local project tree. The exit code is the verdict.

Findings:
    MISSING_ROW             file exists but has no index row
    STALE_ROW               row exists but the file is missing
    DUPLICATE_ROW           same file appears more than once in the index
    MISSING_DRIVE_ID        index row still has TODO-ID or an empty ID
    DUPLICATE_DRIVE_ID      one populated Drive ID is assigned to multiple rows
    MISSING_PROJECT_ID       canonical project ID absent/TODO-ID, or no Drive IDs section
    DUPLICATE_PROJECT_ID     a canonical project ID collides with another one or a row
    UNREADABLE              context file or 00_INSTRUCTIONS is not readable UTF-8 text
    TOO_LARGE               context file exceeds the configured character cap
    DUPLICATE_TOPIC         likely extract/source pair has no Source: relationship
    INVALID_SOURCE_REFERENCE Source: path or Drive ID does not match the project
    MISSING_FRONTMATTER     vault context file lacks required metadata
    BROKEN_LINK             vault wikilink target does not exist

Exit codes: 0 clean, 1 findings, 2 usage error. Exit 2 covers a missing project path
(00_INSTRUCTIONS.md, 01_INDEX.md, 90_LOG.md, 10_context or 20_sources) and an index
that is not UTF-8 text.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

from common import (
    CONTEXT_DIR,
    DEFAULT_MAX_CHARS,
    DRIVE_IDS_HEADING,
    FRONTMATTER_REQUIRED,
    INDEX_FILE,
    INSTRUCTIONS_FILE,
    SOURCES_DIR,
    ExitCode,
    IndexRow,
    instruction_drive_ids,
    is_real_drive_id,
    is_vault_project,
    missing_project_paths,
    normalize_stem,
    parse_args_or_exit,
    parse_frontmatter,
    parse_index,
    read_index_or_error,
    read_text,
    scan_files,
    source_reference,
    wikilink_targets,
)

EXIT_OK = ExitCode.OK
EXIT_FINDINGS = ExitCode.FINDINGS
EXIT_USAGE = ExitCode.USAGE


class FindingKind(Enum):
    MISSING_ROW = auto()
    STALE_ROW = auto()
    DUPLICATE_ROW = auto()
    MISSING_DRIVE_ID = auto()
    DUPLICATE_DRIVE_ID = auto()
    MISSING_PROJECT_ID = auto()
    DUPLICATE_PROJECT_ID = auto()
    UNREADABLE = auto()
    TOO_LARGE = auto()
    DUPLICATE_TOPIC = auto()
    INVALID_SOURCE_REFERENCE = auto()
    MISSING_FRONTMATTER = auto()
    BROKEN_LINK = auto()


@dataclass(frozen=True)
class Finding:
    kind: FindingKind
    path: str
    detail: str

    def __str__(self) -> str:
        return f"{self.kind.name} {self.path}: {self.detail}"


def _context_files(files: Sequence[str]) -> list[str]:
    return [f for f in files if f.startswith(CONTEXT_DIR + "/")]


def _source_files(files: Sequence[str]) -> list[str]:
    return [f for f in files if f.startswith(SOURCES_DIR + "/")]


def _is_canonical_location(location: str) -> bool:
    """Whether an identity location is a canonical label of 00_INSTRUCTIONS."""
    return location.startswith(INSTRUCTIONS_FILE + ":")


def _first_rows(rows: Sequence[IndexRow]) -> dict[str, IndexRow]:
    by_file: dict[str, IndexRow] = {}
    for row in rows:
        by_file.setdefault(row.file, row)
    return by_file


def _markdown_targets(root: Path, files: Sequence[str]) -> set[str]:
    targets: set[str] = set()
    for rel in files:
        path = Path(rel)
        if path.suffix.lower() != ".md":
            continue
        without_suffix = path.with_suffix("").as_posix()
        targets.add(without_suffix)
        targets.add(path.stem)
    for top in ("00_INSTRUCTIONS.md", "01_INDEX.md", "90_LOG.md"):
        if (root / top).is_file():
            path = Path(top)
            targets.add(path.with_suffix("").as_posix())
            targets.add(path.stem)
    return targets


def _source_reference_findings(
    rel: str,
    text: str,
    on_disk: set[str],
    rows_by_file: dict[str, IndexRow],
    source_twins: Sequence[str],
) -> list[Finding]:
    reference = source_reference(text)
    if reference is None:
        if source_twins:
            return [
                Finding(
                    FindingKind.DUPLICATE_TOPIC,
                    rel,
                    "same topic as " + ", ".join(source_twins) + " but no 'Source:' line",
                )
            ]
        return []

    source_path, declared_id = reference
    if not source_path.startswith(SOURCES_DIR + "/"):
        return [
            Finding(
                FindingKind.INVALID_SOURCE_REFERENCE,
                rel,
                f"Source path must be under {SOURCES_DIR}/, got {source_path}",
            )
        ]
    if source_path not in on_disk:
        return [
            Finding(
                FindingKind.INVALID_SOURCE_REFERENCE,
                rel,
                f"Source path does not exist: {source_path}",
            )
        ]
    source_row = rows_by_file.get(source_path)
    if (
        declared_id is not None
        and source_row is not None
        and is_real_drive_id(source_row.drive_id)
        and declared_id != source_row.drive_id
    ):
        return [
            Finding(
                FindingKind.INVALID_SOURCE_REFERENCE,
                rel,
                f"Source Drive ID {declared_id} does not match index ID {source_row.drive_id}",
            )
        ]
    return []


def check(root: Path, max_chars: int = DEFAULT_MAX_CHARS) -> list[Finding]:
    """Return every inconsistency between the index and the folder, in stable order."""
    findings: list[Finding] = []
    files = scan_files(root)
    rows = parse_index(read_text(root / INDEX_FILE))
    row_files = [row.file for row in rows]
    indexed = set(row_files)
    on_disk = set(files)
    rows_by_file = _first_rows(rows)

    for rel in files:
        if rel not in indexed:
            findings.append(Finding(FindingKind.MISSING_ROW, rel, "file has no index row"))
    for rel in dict.fromkeys(row_files):
        if rel not in on_disk:
            findings.append(Finding(FindingKind.STALE_ROW, rel, "row exists but file is missing"))
    for rel, count in sorted(Counter(row_files).items()):
        if count > 1:
            findings.append(Finding(FindingKind.DUPLICATE_ROW, rel, f"listed {count} times"))

    for row in rows:
        if not is_real_drive_id(row.drive_id):
            findings.append(
                Finding(FindingKind.MISSING_DRIVE_ID, row.file, "Drive ID is empty or TODO-ID")
            )

    ids: dict[str, list[str]] = {}
    for row in rows:
        if is_real_drive_id(row.drive_id):
            ids.setdefault(row.drive_id, []).append(row.file)
    for drive_id, paths in sorted(ids.items()):
        unique_paths = list(dict.fromkeys(paths))
        if len(unique_paths) > 1:
            findings.append(
                Finding(
                    FindingKind.DUPLICATE_DRIVE_ID,
                    unique_paths[0],
                    f"Drive ID {drive_id} also used by " + ", ".join(unique_paths[1:]),
                )
            )

    instructions_path = root / INSTRUCTIONS_FILE
    try:
        instructions_text: str | None = read_text(instructions_path)
    except (UnicodeDecodeError, OSError) as exc:
        findings.append(
            Finding(FindingKind.UNREADABLE, INSTRUCTIONS_FILE, f"{type(exc).__name__}: {exc}")
        )
        instructions_text = None
    if instructions_text is not None:
        if DRIVE_IDS_HEADING not in instructions_text:
            findings.append(
                Finding(
                    FindingKind.MISSING_PROJECT_ID,
                    INSTRUCTIONS_FILE,
                    "Drive IDs section is missing",
                )
            )
        else:
            project_ids = instruction_drive_ids(instructions_text)
            required_labels = (
                "Project folder",
                "10_context folder",
                "20_sources folder",
                "01_INDEX",
                "90_LOG",
            )
            for label in required_labels:
                value = project_ids.get(label, "")
                if not is_real_drive_id(value):
                    findings.append(
                        Finding(
                            FindingKind.MISSING_PROJECT_ID,
                            INSTRUCTIONS_FILE,
                            f"{label} is empty or TODO-ID",
                        )
                    )

            identity_locations: dict[str, list[str]] = {}
            for row in rows:
                if is_real_drive_id(row.drive_id):
                    identity_locations.setdefault(row.drive_id, []).append(row.file)
            for label in required_labels:
                value = project_ids.get(label, "")
                if is_real_drive_id(value):
                    identity_locations.setdefault(value, []).append(f"{INSTRUCTIONS_FILE}:{label}")
            for drive_id, locations in sorted(identity_locations.items()):
                unique_locations = list(dict.fromkeys(locations))
                canonical = any(_is_canonical_location(loc) for loc in unique_locations)
                if len(unique_locations) > 1 and canonical:
                    findings.append(
                        Finding(
                            FindingKind.DUPLICATE_PROJECT_ID,
                            INSTRUCTIONS_FILE,
                            f"Drive ID {drive_id} reused by " + ", ".join(unique_locations),
                        )
                    )

    sources_by_topic: dict[str, list[str]] = {}
    for rel in _source_files(files):
        sources_by_topic.setdefault(normalize_stem(rel), []).append(rel)

    vault = is_vault_project(root)
    markdown_targets = _markdown_targets(root, files) if vault else set()

    for rel in _context_files(files):
        try:
            text = read_text(root / rel)
        except (UnicodeDecodeError, OSError) as exc:
            findings.append(Finding(FindingKind.UNREADABLE, rel, f"{type(exc).__name__}: {exc}"))
            continue
        if len(text) > max_chars:
            findings.append(
                Finding(FindingKind.TOO_LARGE, rel, f"{len(text)} chars, limit {max_chars}")
            )

        twins = sources_by_topic.get(normalize_stem(rel), [])
        findings.extend(_source_reference_findings(rel, text, on_disk, rows_by_file, twins))

        if vault and Path(rel).suffix.lower() == ".md":
            metadata = parse_frontmatter(text)
            missing_keys = [
                key for key in FRONTMATTER_REQUIRED if not metadata.get(key, "").strip()
            ]
            if missing_keys:
                findings.append(
                    Finding(
                        FindingKind.MISSING_FRONTMATTER,
                        rel,
                        "missing required key(s): " + ", ".join(missing_keys),
                    )
                )
            for target in wikilink_targets(text):
                normalized = target[:-3] if target.lower().endswith(".md") else target
                if (
                    normalized not in markdown_targets
                    and Path(normalized).name not in markdown_targets
                ):
                    findings.append(
                        Finding(
                            FindingKind.BROKEN_LINK,
                            rel,
                            f"wikilink target not found: {target}",
                        )
                    )
    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate 01_INDEX against the folder.")
    parser.add_argument("--root", required=True, type=Path, help="Project folder.")
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
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
    index_text = read_index_or_error(root / INDEX_FILE)
    if isinstance(index_text, int):
        return index_text
    findings = check(root, max_chars=args.max_chars)
    if not findings:
        print("OK: index, identities and folder are consistent")
        return EXIT_OK
    for finding in findings:
        print(finding)
    print(f"{len(findings)} finding(s)")
    return EXIT_FINDINGS


if __name__ == "__main__":
    sys.exit(main())
