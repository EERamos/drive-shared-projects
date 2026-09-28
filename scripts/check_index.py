"""Validate 01_INDEX against the local project tree. The exit code is the verdict.

Findings:
    MISSING_ROW             file exists but has no index row
    STALE_ROW               row exists but the file is missing
    DUPLICATE_ROW           same file appears more than once in the index
    MISSING_DRIVE_ID        index row has TODO-ID or no ID, or vault frontmatter has TODO-ID
    DUPLICATE_DRIVE_ID      one populated Drive ID is assigned to multiple rows
    NESTED_FOLDER           a folder inside 10_context or 20_sources; both stay flat
    MISSING_PROJECT_ID       canonical project ID absent/TODO-ID, or no Drive IDs section
    DUPLICATE_PROJECT_ID     a canonical project ID collides with another one or a row
    UNREADABLE              context file or 00_INSTRUCTIONS is not readable UTF-8 text
    TOO_LARGE               context file exceeds the configured cap in UTF-8 bytes
    INVALID_SOURCE_REFERENCE Source: path or Drive ID does not match the project
    ID_MISMATCH             a frontmatter drive_id and the file's index row disagree
    MISSING_FRONTMATTER     vault context file lacks required metadata
    BROKEN_LINK             vault wikilink or embed target is not a file of the project

Exit codes: 0 clean, 1 findings, 2 usage error. Exit 2 covers a missing project path
(00_INSTRUCTIONS.md, 01_INDEX.md, 90_LOG.md, 10_context or 20_sources) and an index
that is not UTF-8 text.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path, PurePosixPath

from common import (
    CONTEXT_DIR,
    DEFAULT_MAX_CHARS,
    FRONTMATTER_REQUIRED,
    ID_PLACEHOLDER,
    INDEX_FILE,
    INSTRUCTIONS_FILE,
    REQUIRED_FILES,
    SCANNED_DIRS,
    SOURCES_DIR,
    TEXT_SUFFIXES,
    ExitCode,
    IndexRow,
    canonical_id_collisions,
    duplicate_drive_id_paths,
    duplicate_row_counts,
    first_rows_by_file,
    is_hidden_path,
    is_real_drive_id,
    is_vault_project,
    missing_canonical_ids,
    missing_project_paths,
    parse_args_or_exit,
    parse_frontmatter,
    parse_index,
    read_index_or_error,
    read_text,
    relative_posix,
    scan_files,
    source_reference,
    use_utf8_output,
    wikilinks,
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
    NESTED_FOLDER = auto()
    MISSING_PROJECT_ID = auto()
    DUPLICATE_PROJECT_ID = auto()
    UNREADABLE = auto()
    TOO_LARGE = auto()
    INVALID_SOURCE_REFERENCE = auto()
    ID_MISMATCH = auto()
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


def _nested_folders(root: Path) -> list[str]:
    """Folders directly inside 10_context and 20_sources; dot folders are skipped like dotfiles."""
    nested: list[str] = []
    for sub in SCANNED_DIRS:
        base = root / sub
        if base.is_dir():
            nested.extend(
                relative_posix(root, path)
                for path in base.iterdir()
                if path.is_dir() and not is_hidden_path(path.name)
            )
    return sorted(nested)


def _link_targets(root: Path, files: Sequence[str]) -> set[str]:
    """Lowercased names a wikilink may use for a project file, the way Obsidian resolves them.

    Every file under 10_context and 20_sources and the three root files resolve by full
    path or by file name with its extension; a Markdown note also resolves without `.md`.
    """
    top = [name for name in REQUIRED_FILES if (root / name).is_file()]
    targets: set[str] = set()
    for rel in [*files, *top]:
        path = PurePosixPath(rel.lower())
        targets.update((path.as_posix(), path.name))
        if path.suffix == ".md":
            targets.update((path.with_suffix("").as_posix(), path.stem))
    return targets


def _broken_link_detail(target: str, embed: bool) -> str:
    if embed:
        return (
            f"embed target not found: {target}; keep embedded files in the project, "
            "originals in 20_sources with an index row"
        )
    return f"wikilink target not found: {target}"


def _source_reference_findings(
    rel: str,
    text: str,
    on_disk: set[str],
    rows_by_file: dict[str, IndexRow],
) -> list[Finding]:
    reference = source_reference(text)
    if reference is None:
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


def _frontmatter_drive_id(text: str) -> str:
    return parse_frontmatter(text).get("drive_id", "").strip()


def _identity_findings(rel: str, frontmatter_id: str, row: IndexRow | None) -> list[Finding]:
    """ID_MISMATCH when the frontmatter and the index row both carry an ID and they differ.

    build_index lets a frontmatter ID replace the row's ID in any project, so the check
    covers every text file it reads, vault or not.
    """
    if row is None or not is_real_drive_id(frontmatter_id) or not is_real_drive_id(row.drive_id):
        return []
    if frontmatter_id == row.drive_id:
        return []
    return [
        Finding(
            FindingKind.ID_MISMATCH,
            rel,
            f"frontmatter drive_id {frontmatter_id} != index ID {row.drive_id}",
        )
    ]


def check(root: Path, max_chars: int = DEFAULT_MAX_CHARS) -> list[Finding]:
    """Return every inconsistency between the index and the folder, in stable order."""
    findings: list[Finding] = []
    files = scan_files(root)
    rows = parse_index(read_text(root / INDEX_FILE))
    row_files = [row.file for row in rows]
    indexed = set(row_files)
    on_disk = set(files)
    rows_by_file = first_rows_by_file(rows)

    for rel in files:
        if rel not in indexed:
            findings.append(Finding(FindingKind.MISSING_ROW, rel, "file has no index row"))
    for rel in dict.fromkeys(row_files):
        if rel not in on_disk:
            findings.append(Finding(FindingKind.STALE_ROW, rel, "row exists but file is missing"))
    for rel, count in duplicate_row_counts(rows):
        findings.append(Finding(FindingKind.DUPLICATE_ROW, rel, f"listed {count} times"))

    for row in rows:
        if not is_real_drive_id(row.drive_id):
            findings.append(
                Finding(FindingKind.MISSING_DRIVE_ID, row.file, "Drive ID is empty or TODO-ID")
            )

    for drive_id, unique_paths in duplicate_drive_id_paths(rows):
        findings.append(
            Finding(
                FindingKind.DUPLICATE_DRIVE_ID,
                unique_paths[0],
                f"Drive ID {drive_id} also used by " + ", ".join(unique_paths[1:]),
            )
        )

    for rel in _nested_folders(root):
        folder = rel.split("/", 1)[0]
        findings.append(
            Finding(
                FindingKind.NESTED_FOLDER,
                rel,
                f"folder inside {folder}; keep it flat, the Drive check does not look inside it",
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
        missing_ids = missing_canonical_ids(instructions_text)
        if missing_ids is None:
            findings.append(
                Finding(
                    FindingKind.MISSING_PROJECT_ID,
                    INSTRUCTIONS_FILE,
                    "Drive IDs section is missing",
                )
            )
        else:
            for label in missing_ids:
                findings.append(
                    Finding(
                        FindingKind.MISSING_PROJECT_ID,
                        INSTRUCTIONS_FILE,
                        f"{label} is empty or TODO-ID",
                    )
                )
            for drive_id, unique_locations in canonical_id_collisions(instructions_text, rows):
                findings.append(
                    Finding(
                        FindingKind.DUPLICATE_PROJECT_ID,
                        INSTRUCTIONS_FILE,
                        f"Drive ID {drive_id} reused by " + ", ".join(unique_locations),
                    )
                )

    vault = is_vault_project(root)
    link_targets = _link_targets(root, files) if vault else set()

    for rel in _context_files(files):
        try:
            text = read_text(root / rel)
        except (UnicodeDecodeError, OSError) as exc:
            findings.append(Finding(FindingKind.UNREADABLE, rel, f"{type(exc).__name__}: {exc}"))
            continue
        # The connector limit was observed in bytes. A UTF-8 byte count is never below the
        # character count, so capping the bytes caps the characters too.
        size = len(text.encode("utf-8"))
        if size > max_chars:
            findings.append(
                Finding(
                    FindingKind.TOO_LARGE,
                    rel,
                    f"{len(text)} chars, {size} UTF-8 bytes, limit {max_chars}",
                )
            )

        findings.extend(_source_reference_findings(rel, text, on_disk, rows_by_file))
        if Path(rel).suffix.lower() in TEXT_SUFFIXES:
            findings.extend(
                _identity_findings(rel, _frontmatter_drive_id(text), rows_by_file.get(rel))
            )

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
            if metadata.get("drive_id", "").strip() == ID_PLACEHOLDER:
                findings.append(
                    Finding(
                        FindingKind.MISSING_DRIVE_ID,
                        rel,
                        f"frontmatter drive_id is {ID_PLACEHOLDER}",
                    )
                )
            for target, embed in wikilinks(text):
                wanted = PurePosixPath(target.lower())
                if wanted.as_posix() in link_targets or wanted.name in link_targets:
                    continue
                findings.append(
                    Finding(FindingKind.BROKEN_LINK, rel, _broken_link_detail(target, embed))
                )

    for rel in files:
        if not rel.startswith(SOURCES_DIR + "/") or Path(rel).suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = read_text(root / rel)
        except (UnicodeDecodeError, OSError):
            continue  # build_index reads no identity from it either
        findings.extend(_identity_findings(rel, _frontmatter_drive_id(text), rows_by_file.get(rel)))
    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate 01_INDEX against the folder.")
    parser.add_argument("--root", required=True, type=Path, help="Project folder.")
    parser.add_argument(
        "--max-chars",
        type=int,
        default=DEFAULT_MAX_CHARS,
        help="Cap for every context file, applied to its UTF-8 byte count.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    use_utf8_output()
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
