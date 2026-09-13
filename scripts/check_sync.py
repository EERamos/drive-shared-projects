"""Compare a local project tree with an exported Google Drive listing CSV.

CSV columns: `path,drive_id`. Paths are relative to the project folder and use `/`.
The command reports files present on only one side, populated IDs that disagree and
IDs recorded on only one side. 00_INSTRUCTIONS.md has no local self-ID by design, so
an empty local ID is not a finding for that path.

Findings:
    LOCAL_ONLY   local file is absent from the Drive listing
    DRIVE_ONLY   Drive file is absent from the local project
    ID_MISMATCH  both sides have a populated ID and they disagree
    ID_MISSING   the path exists on both sides but only one side records an ID

Exit codes: 0 clean, 1 findings, 2 usage error. Exit 2 covers a missing project path
(00_INSTRUCTIONS.md, 01_INDEX.md, 90_LOG.md, 10_context or 20_sources), an index that
is not UTF-8 text and a Drive CSV that cannot be read.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

from common import (
    INDEX_FILE,
    INSTRUCTIONS_FILE,
    LOG_FILE,
    ExitCode,
    instruction_drive_ids,
    is_real_drive_id,
    missing_project_paths,
    parse_args_or_exit,
    parse_drive_csv,
    parse_index,
    project_files,
    read_index_or_error,
    read_text_or_error,
)

EXIT_OK = ExitCode.OK
EXIT_FINDINGS = ExitCode.FINDINGS
EXIT_USAGE = ExitCode.USAGE


class SyncFindingKind(Enum):
    LOCAL_ONLY = auto()
    DRIVE_ONLY = auto()
    ID_MISMATCH = auto()
    ID_MISSING = auto()


@dataclass(frozen=True)
class SyncFinding:
    kind: SyncFindingKind
    path: str
    detail: str

    def __str__(self) -> str:
        return f"{self.kind.name} {self.path}: {self.detail}"


def read_drive_csv(path: Path) -> dict[str, str]:
    """Read `path,drive_id` rows from a UTF-8 CSV file."""
    return parse_drive_csv(path.read_text(encoding="utf-8"))


def local_drive_ids(index_text: str, instructions_text: str) -> dict[str, str]:
    """Return known local identities for project files, from texts read by the caller."""
    ids: dict[str, str] = {row.file: row.drive_id for row in parse_index(index_text)}
    recorded = instruction_drive_ids(instructions_text)
    ids[INDEX_FILE] = recorded.get("01_INDEX", "")
    ids[LOG_FILE] = recorded.get("90_LOG", "")
    # 00_INSTRUCTIONS intentionally has no self-ID; its path is still compared.
    ids.setdefault(INSTRUCTIONS_FILE, "")
    return ids


def check_sync(
    root: Path,
    drive_rows: dict[str, str],
    index_text: str,
    instructions_text: str,
) -> list[SyncFinding]:
    """Compare local files and identities with one Drive listing.

    `index_text` and `instructions_text` are read once by the caller, which is also
    where an unreadable file is turned into a usage error.
    """
    findings: list[SyncFinding] = []
    local = set(project_files(root))
    remote = set(drive_rows)
    ids = local_drive_ids(index_text, instructions_text)

    for rel in sorted(local - remote):
        findings.append(SyncFinding(SyncFindingKind.LOCAL_ONLY, rel, "missing from Drive listing"))
    for rel in sorted(remote - local):
        findings.append(SyncFinding(SyncFindingKind.DRIVE_ONLY, rel, "missing from local project"))
    for rel in sorted(local & remote):
        local_id = ids.get(rel, "")
        remote_id = drive_rows.get(rel, "")
        has_local = is_real_drive_id(local_id)
        has_remote = is_real_drive_id(remote_id)
        if has_local and has_remote:
            if local_id != remote_id:
                findings.append(
                    SyncFinding(
                        SyncFindingKind.ID_MISMATCH,
                        rel,
                        f"local ID {local_id} != Drive ID {remote_id}",
                    )
                )
        elif has_remote and rel != INSTRUCTIONS_FILE:
            # 00_INSTRUCTIONS has no local self-ID by design; every other path needs one.
            findings.append(
                SyncFinding(
                    SyncFindingKind.ID_MISSING,
                    rel,
                    f"local ID missing (Drive has {remote_id})",
                )
            )
        elif has_local:
            findings.append(
                SyncFinding(
                    SyncFindingKind.ID_MISSING,
                    rel,
                    f"Drive ID missing (local has {local_id})",
                )
            )
    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare a project with a Drive listing CSV.")
    parser.add_argument("--root", required=True, type=Path, help="Local project folder.")
    parser.add_argument(
        "--drive-csv",
        required=True,
        type=Path,
        help="CSV with path,drive_id columns.",
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
    index_text = read_index_or_error(root / INDEX_FILE)
    if isinstance(index_text, int):
        return index_text
    instructions_text = read_text_or_error(root / INSTRUCTIONS_FILE)
    if isinstance(instructions_text, int):
        return instructions_text
    try:
        drive_rows = read_drive_csv(args.drive_csv)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        print(f"error: cannot read Drive CSV: {exc}", file=sys.stderr)
        return EXIT_USAGE
    findings = check_sync(root, drive_rows, index_text, instructions_text)
    if not findings:
        print("OK: local project and Drive listing are synchronized")
        return EXIT_OK
    for finding in findings:
        print(finding)
    print(f"{len(findings)} finding(s)")
    return EXIT_FINDINGS


if __name__ == "__main__":
    sys.exit(main())
