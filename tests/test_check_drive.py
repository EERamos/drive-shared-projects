"""check_drive validates 01_INDEX against Drive listings saved from the connector."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from check_drive import (
    EXIT_FINDINGS,
    EXIT_OK,
    EXIT_USAGE,
    DriveFinding,
    DriveFindingKind,
    ListingError,
    check_drive,
    main,
)
from common import FOLDER_MIME_TYPE, DriveEntry, IndexRow, parse_listing, render_index_table

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "connector"
PROJECT = "1_project_folder_000000000000000A"
CONTEXT = "1_context_folder_000000000000000B"
SOURCES = "1_sources_folder_000000000000000C"
INDEX_ID = "1_index_doc_000000000000000000000000000000-D"
LOG_ID = "1_log_doc_00000000000000000000000000000000-E"
DOC = "application/vnd.google-apps.document"


def _instructions(overrides: dict[str, str] | None = None) -> str:
    values = {
        "Project folder": PROJECT,
        "10_context folder": CONTEXT,
        "20_sources folder": SOURCES,
        "01_INDEX": INDEX_ID,
        "90_LOG": LOG_ID,
        **(overrides or {}),
    }
    lines = "\n".join(f"- {label}: {value}" for label, value in values.items())
    return f"# P\n\nMode: duo. Format: docs.\n\n## Drive IDs\n\n{lines}\n"


def _index(rows: Sequence[IndexRow]) -> str:
    header = "# Index\n\nIndex owner: Ana. Last updated: 2026-09-13.\n\n## Files\n\n"
    return header + render_index_table(rows)


def _entry(drive_id: str, title: str, parent: str, mime: str = DOC) -> DriveEntry:
    return DriveEntry(drive_id, title, mime, parent, None)


def _shape(findings: Sequence[DriveFinding]) -> list[tuple[DriveFindingKind, str]]:
    return [(finding.kind, finding.path) for finding in findings]


def _fixture_argv(index_name: str, *listings: str) -> list[str]:
    argv = [
        "--instructions",
        str(FIXTURES / "00_INSTRUCTIONS.json"),
        "--index",
        str(FIXTURES / index_name),
    ]
    for listing in listings:
        argv += ["--listing", str(FIXTURES / listing)]
    return argv


def test_clean_docs_project_from_real_fixtures_is_clean(
    capsys: pytest.CaptureFixture[str],
) -> None:
    argv = _fixture_argv(
        "01_INDEX_clean.json", "10_context.json", "20_sources.json", "project.json"
    )
    assert main(argv) == EXIT_OK
    assert capsys.readouterr().out.startswith("OK")


def test_fresh_index_fixture_reports_placeholders_and_the_unindexed_file(
    capsys: pytest.CaptureFixture[str],
) -> None:
    argv = _fixture_argv("01_INDEX.json", "10_context.json", "20_sources.json")
    assert main(argv) == EXIT_FINDINGS
    out = capsys.readouterr().out
    assert "MISSING_DRIVE_ID 10_context/Momentum backtest 2026:" in out
    assert "MISSING_DRIVE_ID 20_sources/momentum_backtest_2026.md:" in out
    assert "MISSING_ROW 10_context/pricing_notes.md:" in out
    assert "3 finding(s)" in out


def test_reports_missing_and_stale_rows() -> None:
    rows = [IndexRow("10_context/Gone", "1gone", "G", "always", "Ana")]
    entries = [_entry("1new", "New", CONTEXT)]
    assert _shape(check_drive(_instructions(), _index(rows), entries)) == [
        (DriveFindingKind.MISSING_ROW, "10_context/New"),
        (DriveFindingKind.STALE_ROW, "10_context/Gone"),
    ]


def test_reports_id_mismatch_for_the_same_path() -> None:
    rows = [IndexRow("20_sources/a.pdf", "1old", "A", "detail", "Ana")]
    entries = [_entry("1new", "a.pdf", SOURCES, "application/pdf")]
    (finding,) = check_drive(_instructions(), _index(rows), entries)
    assert finding.kind is DriveFindingKind.ID_MISMATCH
    assert finding.path == "20_sources/a.pdf"
    assert "1old" in finding.detail and "1new" in finding.detail


def test_detects_a_rename_by_stable_drive_id() -> None:
    rows = [IndexRow("10_context/Old title", "1same", "A", "always", "Ana")]
    entries = [_entry("1same", "New title", CONTEXT)]
    (finding,) = check_drive(_instructions(), _index(rows), entries)
    assert finding.kind is DriveFindingKind.RENAMED_FILE
    assert finding.path == "10_context/Old title"
    assert "10_context/New title" in finding.detail


def test_reports_duplicate_titles_inside_a_folder() -> None:
    rows = [IndexRow("10_context/Topic", "1a", "A", "always", "Ana")]
    entries = [_entry("1a", "Topic", CONTEXT), _entry("1b", "Topic", CONTEXT)]
    findings = check_drive(_instructions(), _index(rows), entries)
    assert _shape(findings) == [(DriveFindingKind.DUPLICATE_TITLE, "10_context/Topic")]
    assert "1a" in findings[0].detail and "1b" in findings[0].detail


def test_reports_nested_folders_instead_of_descending() -> None:
    entries = [_entry("1sub", "archive", CONTEXT, FOLDER_MIME_TYPE)]
    findings = check_drive(_instructions(), _index([]), entries)
    assert _shape(findings) == [(DriveFindingKind.NESTED_FOLDER, "10_context/archive")]


def test_listing_from_an_unknown_folder_is_a_listing_error() -> None:
    with pytest.raises(ListingError, match="1_unknown_parent"):
        check_drive(_instructions(), _index([]), [_entry("1x", "Stray", "1_unknown_parent")])


def test_entry_without_parent_is_a_listing_error() -> None:
    entry = DriveEntry("1x", "Stray", DOC, None, None)
    with pytest.raises(ListingError, match="parentId"):
        check_drive(_instructions(), _index([]), [entry])


def test_root_listing_checks_canonical_entries_in_a_fixed_order() -> None:
    entries = [
        _entry("1other", "01_INDEX", PROJECT),
        _entry(CONTEXT, "10_context", PROJECT, FOLDER_MIME_TYPE),
        _entry(SOURCES, "20_sources", PROJECT, FOLDER_MIME_TYPE),
        _entry("1instr", "00_INSTRUCTIONS", PROJECT),
        _entry("1stray", "notes.pdf", PROJECT, "application/pdf"),
    ]
    findings = check_drive(_instructions(), _index([]), entries)
    assert _shape(findings) == [
        (DriveFindingKind.ID_MISMATCH, "01_INDEX"),
        (DriveFindingKind.MISSING_CANONICAL_FILE, "90_LOG"),
        (DriveFindingKind.UNEXPECTED_FILE, "notes.pdf"),
    ]


def test_root_listing_accepts_md_named_canonical_files() -> None:
    entries = [
        _entry("1instr", "00_INSTRUCTIONS.md", PROJECT, "text/markdown"),
        _entry(INDEX_ID, "01_INDEX.md", PROJECT, "text/markdown"),
        _entry(LOG_ID, "90_LOG.md", PROJECT, "text/markdown"),
        _entry(CONTEXT, "10_context", PROJECT, FOLDER_MIME_TYPE),
        _entry(SOURCES, "20_sources", PROJECT, FOLDER_MIME_TYPE),
    ]
    assert check_drive(_instructions(), _index([]), entries) == []


def test_missing_project_ids_are_reported_and_block_listing_resolution() -> None:
    text = _instructions({"10_context folder": "TODO-ID"})
    findings = check_drive(text, _index([]), [])
    assert _shape(findings) == [(DriveFindingKind.MISSING_PROJECT_ID, "00_INSTRUCTIONS.md")]
    assert "10_context folder" in findings[0].detail
    with pytest.raises(ListingError):
        check_drive(text, _index([]), [_entry("1x", "Topic", CONTEXT)])


def test_missing_drive_ids_section_is_a_finding() -> None:
    findings = check_drive("# P\n", _index([]), [])
    assert _shape(findings) == [(DriveFindingKind.MISSING_PROJECT_ID, "00_INSTRUCTIONS.md")]
    assert "section is missing" in findings[0].detail


def test_canonical_id_collisions_are_reported() -> None:
    rows = [IndexRow("10_context/A", CONTEXT, "A", "always", "Ana")]
    findings = check_drive(_instructions(), _index(rows), [_entry(CONTEXT, "A", CONTEXT)])
    assert _shape(findings) == [
        (DriveFindingKind.DUPLICATE_PROJECT_ID, "00_INSTRUCTIONS.md"),
    ]


def test_index_structure_findings_come_before_the_comparison() -> None:
    rows = [
        IndexRow("10_context/A", "TODO-ID", "A", "always", "Ana"),
        IndexRow("10_context/A", "1a", "A", "always", "Ana"),
        IndexRow("10_context/B", "1b", "B", "always", "Ana"),
        IndexRow("10_context/C", "1b", "C", "always", "Ana"),
    ]
    entries = [_entry("1a", "A", CONTEXT), _entry("1b", "B", CONTEXT), _entry("1c", "C", CONTEXT)]
    assert _shape(check_drive(_instructions(), _index(rows), entries)) == [
        (DriveFindingKind.DUPLICATE_ROW, "10_context/A"),
        (DriveFindingKind.MISSING_DRIVE_ID, "10_context/A"),
        (DriveFindingKind.DUPLICATE_DRIVE_ID, "10_context/B"),
        (DriveFindingKind.ID_MISMATCH, "10_context/C"),
    ]


def test_csv_listing_paths_are_used_directly() -> None:
    rows = [
        IndexRow("10_context/topic.md", "1t", "T", "always", "Ana"),
        IndexRow("20_sources/source.pdf", "1s", "S", "detail", "Ana"),
    ]
    listing = "path,drive_id\n10_context/topic.md,1t\n20_sources/source.pdf,1s\n"
    assert check_drive(_instructions(), _index(rows), parse_listing(listing)) == []


def test_main_reports_unreadable_or_malformed_inputs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    instructions = tmp_path / "instructions.json"
    instructions.write_text(json.dumps({"fileContent": _instructions()}), encoding="utf-8")
    index = tmp_path / "index.json"
    index.write_text(json.dumps({"fileContent": _index([])}), encoding="utf-8")
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    base = ["--instructions", str(instructions), "--index", str(index)]

    assert main([*base, "--listing", str(bad)]) == EXIT_USAGE
    assert "bad.json" in capsys.readouterr().err
    missing = str(tmp_path / "missing.json")
    assert main(["--instructions", missing, "--index", str(index), "--listing", str(bad)]) == 2
    assert main([*base, "--listing", str(instructions)]) == EXIT_USAGE


def test_main_turns_listing_errors_into_usage_errors(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    instructions = tmp_path / "instructions.md"
    instructions.write_text(_instructions(), encoding="utf-8")
    index = tmp_path / "index.md"
    index.write_text(_index([]), encoding="utf-8")
    listing = tmp_path / "listing.json"
    listing.write_text(
        json.dumps({"files": [{"id": "1x", "title": "Stray", "parentId": "1_elsewhere"}]}),
        encoding="utf-8",
    )
    argv = ["--instructions", str(instructions), "--index", str(index), "--listing", str(listing)]
    assert main(argv) == EXIT_USAGE
    assert "1_elsewhere" in capsys.readouterr().err


def test_main_requires_at_least_one_listing() -> None:
    assert main(["--instructions", "a.json", "--index", "b.json"]) == EXIT_USAGE
