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
    Listing,
    ListingError,
    check_drive,
    main,
)
from common import (
    CONTEXT_DIR,
    FOLDER_MIME_TYPE,
    SOURCES_DIR,
    DriveEntry,
    IndexRow,
    parse_listing,
    render_index_table,
)

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


def _listings(
    context: Sequence[DriveEntry] = (),
    sources: Sequence[DriveEntry] = (),
    project: Sequence[DriveEntry] | None = None,
) -> list[Listing]:
    listings = [Listing(CONTEXT_DIR, tuple(context)), Listing(SOURCES_DIR, tuple(sources))]
    if project is not None:
        listings.append(Listing("", tuple(project)))
    return listings


def _clean_root() -> list[DriveEntry]:
    return [
        _entry("1instr", "00_INSTRUCTIONS", PROJECT),
        _entry(INDEX_ID, "01_INDEX", PROJECT),
        _entry(LOG_ID, "90_LOG", PROJECT),
        _entry(CONTEXT, "10_context", PROJECT, FOLDER_MIME_TYPE),
        _entry(SOURCES, "20_sources", PROJECT, FOLDER_MIME_TYPE),
    ]


def _fixture_argv(index_name: str, *, project: bool) -> list[str]:
    argv = [
        "--instructions",
        str(FIXTURES / "00_INSTRUCTIONS.json"),
        "--index",
        str(FIXTURES / index_name),
        "--context-listing",
        str(FIXTURES / "10_context.json"),
        "--sources-listing",
        str(FIXTURES / "20_sources.json"),
    ]
    if project:
        argv += ["--project-listing", str(FIXTURES / "project.json")]
    return argv


def test_clean_docs_project_from_real_fixtures_is_clean(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(_fixture_argv("01_INDEX_clean.json", project=True)) == EXIT_OK
    assert capsys.readouterr().out.startswith("OK")


def test_clean_run_without_project_listing_says_so(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(_fixture_argv("01_INDEX_clean.json", project=False)) == EXIT_OK
    out = capsys.readouterr().out
    assert out.startswith("OK")
    assert "project folder not listed" in out


def test_fresh_index_fixture_reports_placeholders_and_the_unindexed_file(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(_fixture_argv("01_INDEX.json", project=False)) == EXIT_FINDINGS
    out = capsys.readouterr().out
    assert "MISSING_DRIVE_ID 10_context/Momentum backtest 2026:" in out
    assert "MISSING_DRIVE_ID 20_sources/momentum_backtest_2026.md:" in out
    assert "MISSING_ROW 10_context/pricing_notes.md:" in out
    assert "3 finding(s)" in out


def test_both_content_listings_are_required() -> None:
    with pytest.raises(ListingError, match="20_sources"):
        check_drive(_instructions(), _index([]), [Listing(CONTEXT_DIR, ())])
    with pytest.raises(ListingError, match="10_context"):
        check_drive(_instructions(), _index([]), [Listing(SOURCES_DIR, ())])


def test_a_folder_listed_twice_is_a_listing_error() -> None:
    with pytest.raises(ListingError, match="twice"):
        check_drive(_instructions(), _index([]), [*_listings(), Listing(CONTEXT_DIR, ())])


def test_empty_listings_keep_their_identity() -> None:
    assert check_drive(_instructions(), _index([]), _listings()) == []
    rows = [IndexRow("20_sources/a.pdf", "1a", "A", "detail", "Ana")]
    findings = check_drive(_instructions(), _index(rows), _listings())
    assert _shape(findings) == [(DriveFindingKind.STALE_ROW, "20_sources/a.pdf")]


def test_empty_project_listing_reports_every_canonical_entry_missing() -> None:
    findings = check_drive(_instructions(), _index([]), _listings(project=[]))
    assert [finding.kind for finding in findings] == [DriveFindingKind.MISSING_CANONICAL_FILE] * 5


def test_reports_missing_and_stale_rows() -> None:
    rows = [IndexRow("10_context/Gone", "1gone", "G", "always", "Ana")]
    listings = _listings(context=[_entry("1new", "New", CONTEXT)])
    assert _shape(check_drive(_instructions(), _index(rows), listings)) == [
        (DriveFindingKind.MISSING_ROW, "10_context/New"),
        (DriveFindingKind.STALE_ROW, "10_context/Gone"),
    ]


def test_reports_id_mismatch_for_the_same_path() -> None:
    rows = [IndexRow("20_sources/a.pdf", "1old", "A", "detail", "Ana")]
    listings = _listings(sources=[_entry("1new", "a.pdf", SOURCES, "application/pdf")])
    (finding,) = check_drive(_instructions(), _index(rows), listings)
    assert finding.kind is DriveFindingKind.ID_MISMATCH
    assert finding.path == "20_sources/a.pdf"
    assert "1old" in finding.detail and "1new" in finding.detail


def test_detects_a_rename_by_stable_drive_id() -> None:
    rows = [IndexRow("10_context/Old title", "1same", "A", "always", "Ana")]
    listings = _listings(context=[_entry("1same", "New title", CONTEXT)])
    (finding,) = check_drive(_instructions(), _index(rows), listings)
    assert finding.kind is DriveFindingKind.RENAMED_FILE
    assert finding.path == "10_context/Old title"
    assert "10_context/New title" in finding.detail


def test_reports_duplicate_titles_inside_a_folder() -> None:
    rows = [IndexRow("10_context/Topic", "1a", "A", "always", "Ana")]
    listings = _listings(context=[_entry("1a", "Topic", CONTEXT), _entry("1b", "Topic", CONTEXT)])
    findings = check_drive(_instructions(), _index(rows), listings)
    assert _shape(findings) == [(DriveFindingKind.DUPLICATE_TITLE, "10_context/Topic")]
    assert "1a" in findings[0].detail and "1b" in findings[0].detail


def test_reports_nested_folders_instead_of_descending() -> None:
    listings = _listings(context=[_entry("1sub", "archive", CONTEXT, FOLDER_MIME_TYPE)])
    findings = check_drive(_instructions(), _index([]), listings)
    assert _shape(findings) == [(DriveFindingKind.NESTED_FOLDER, "10_context/archive")]


def test_entries_from_another_folder_are_a_listing_error() -> None:
    with pytest.raises(ListingError, match=SOURCES):
        check_drive(
            _instructions(), _index([]), _listings(context=[_entry("1x", "Stray", SOURCES)])
        )
    stray = _entry("1x", "Stray", "1_unknown_parent")
    with pytest.raises(ListingError, match="1_unknown_parent"):
        check_drive(_instructions(), _index([]), _listings(context=[stray]))
    with pytest.raises(ListingError, match=CONTEXT):
        check_drive(
            _instructions(), _index([]), _listings(project=[_entry("1x", "01_INDEX", CONTEXT)])
        )


def test_entry_without_parent_is_a_listing_error() -> None:
    entry = DriveEntry("1x", "Stray", DOC, None, None)
    with pytest.raises(ListingError, match="parentId"):
        check_drive(_instructions(), _index([]), _listings(context=[entry]))


def test_csv_rows_outside_the_listed_folder_are_a_listing_error() -> None:
    rows = parse_listing("path,drive_id\n20_sources/source.pdf,1s\n")
    with pytest.raises(ListingError, match="20_sources/source.pdf"):
        check_drive(_instructions(), _index([]), _listings(context=rows))
    with pytest.raises(ListingError, match="20_sources/source.pdf"):
        check_drive(_instructions(), _index([]), _listings(project=rows))


def test_listing_for_a_folder_without_recorded_id_is_a_listing_error() -> None:
    text = _instructions({"10_context folder": "TODO-ID"})
    with pytest.raises(ListingError, match="10_context folder"):
        check_drive(text, _index([]), _listings())
    with pytest.raises(ListingError, match="Drive IDs section"):
        check_drive("# P\n", _index([]), _listings())


def test_missing_project_ids_are_reported() -> None:
    text = _instructions({"Project folder": "TODO-ID", "90_LOG": "TODO-ID"})
    findings = check_drive(text, _index([]), _listings())
    assert _shape(findings) == [(DriveFindingKind.MISSING_PROJECT_ID, "00_INSTRUCTIONS.md")] * 2
    assert "Project folder" in findings[0].detail
    assert "90_LOG" in findings[1].detail


def test_root_listing_checks_canonical_entries_in_a_fixed_order() -> None:
    project = [
        _entry("1other", "01_INDEX", PROJECT),
        _entry(CONTEXT, "10_context", PROJECT, FOLDER_MIME_TYPE),
        _entry(SOURCES, "20_sources", PROJECT, FOLDER_MIME_TYPE),
        _entry("1instr", "00_INSTRUCTIONS", PROJECT),
        _entry("1stray", "notes.pdf", PROJECT, "application/pdf"),
    ]
    findings = check_drive(_instructions(), _index([]), _listings(project=project))
    assert _shape(findings) == [
        (DriveFindingKind.ID_MISMATCH, "01_INDEX"),
        (DriveFindingKind.MISSING_CANONICAL_FILE, "90_LOG"),
        (DriveFindingKind.UNEXPECTED_FILE, "notes.pdf"),
    ]


def test_root_listing_accepts_md_named_canonical_files() -> None:
    project = [
        _entry("1instr", "00_INSTRUCTIONS.md", PROJECT, "text/markdown"),
        _entry(INDEX_ID, "01_INDEX.md", PROJECT, "text/markdown"),
        _entry(LOG_ID, "90_LOG.md", PROJECT, "text/markdown"),
        _entry(CONTEXT, "10_context", PROJECT, FOLDER_MIME_TYPE),
        _entry(SOURCES, "20_sources", PROJECT, FOLDER_MIME_TYPE),
    ]
    assert check_drive(_instructions(), _index([]), _listings(project=project)) == []


def test_root_listing_reports_both_variants_of_a_canonical_file() -> None:
    project = [*_clean_root(), _entry("1other", "01_INDEX.md", PROJECT, "text/markdown")]
    findings = check_drive(_instructions(), _index([]), _listings(project=project))
    assert _shape(findings) == [(DriveFindingKind.DUPLICATE_CANONICAL_FILE, "01_INDEX")]
    assert "01_INDEX.md" in findings[0].detail
    assert "1other" in findings[0].detail


def test_canonical_id_collisions_are_reported() -> None:
    rows = [IndexRow("10_context/A", CONTEXT, "A", "always", "Ana")]
    listings = _listings(context=[_entry(CONTEXT, "A", CONTEXT)])
    findings = check_drive(_instructions(), _index(rows), listings)
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
    context = [_entry("1a", "A", CONTEXT), _entry("1b", "B", CONTEXT), _entry("1c", "C", CONTEXT)]
    findings = check_drive(_instructions(), _index(rows), _listings(context=context))
    assert _shape(findings) == [
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
    context = parse_listing("path,drive_id\n10_context/topic.md,1t\n")
    sources = parse_listing("path,drive_id\n20_sources/source.pdf,1s\n")
    listings = _listings(context=context, sources=sources)
    assert check_drive(_instructions(), _index(rows), listings) == []


def test_csv_listing_reports_duplicate_paths() -> None:
    rows = [IndexRow("10_context/topic.md", "1t", "T", "always", "Ana")]
    context = parse_listing("path,drive_id\n10_context/topic.md,1t\n10_context/topic.md,1u\n")
    findings = check_drive(_instructions(), _index(rows), _listings(context=context))
    assert _shape(findings) == [(DriveFindingKind.DUPLICATE_TITLE, "10_context/topic.md")]
    assert "1u" in findings[0].detail


def _saved(tmp_path: Path, name: str, payload: object) -> str:
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def test_main_reports_unreadable_or_malformed_inputs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    instructions = _saved(tmp_path, "instructions.json", {"fileContent": _instructions()})
    index = _saved(tmp_path, "index.json", {"fileContent": _index([])})
    empty = _saved(tmp_path, "empty.json", {"files": []})
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    base = ["--instructions", instructions, "--index", index]

    argv = [*base, "--context-listing", str(bad), "--sources-listing", empty]
    assert main(argv) == EXIT_USAGE
    assert "bad.json" in capsys.readouterr().err
    missing = str(tmp_path / "missing.json")
    argv = ["--instructions", missing, "--index", index, "--context-listing", empty]
    assert main([*argv, "--sources-listing", empty]) == 2
    argv = [*base, "--context-listing", instructions, "--sources-listing", empty]
    assert main(argv) == EXIT_USAGE


def test_main_turns_listing_errors_into_usage_errors(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    instructions = tmp_path / "instructions.md"
    instructions.write_text(_instructions(), encoding="utf-8")
    index = tmp_path / "index.md"
    index.write_text(_index([]), encoding="utf-8")
    stray = {"files": [{"id": "1x", "title": "Stray", "parentId": "1_elsewhere"}]}
    context = _saved(tmp_path, "context.json", stray)
    sources = _saved(tmp_path, "sources.json", {"files": []})
    argv = ["--instructions", str(instructions), "--index", str(index)]
    assert main([*argv, "--context-listing", context, "--sources-listing", sources]) == EXIT_USAGE
    assert "1_elsewhere" in capsys.readouterr().err


def test_main_requires_both_content_listings() -> None:
    argv = ["--instructions", "a.json", "--index", "b.json", "--context-listing", "c.json"]
    assert main(argv) == EXIT_USAGE
