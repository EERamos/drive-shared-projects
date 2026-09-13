"""Helpers added to common.py so Docs-format projects can be read through the connector."""

from __future__ import annotations

import json
import string
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from common import (
    CANONICAL_LABELS,
    INDEX_HEADER,
    DriveEntry,
    IndexRow,
    canonical_id_collisions,
    connector_markdown,
    first_heading,
    instruction_drive_ids,
    missing_canonical_ids,
    normalize_connector_markdown,
    parse_drive_csv,
    parse_index,
    parse_listing,
    source_reference,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "connector"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_connector_markdown_unwraps_a_saved_read_result() -> None:
    raw = json.dumps({"fileContent": "# Title\n\n  - item one\n"})
    assert connector_markdown(raw) == "# Title\n\n- item one\n"


def test_connector_markdown_passes_plain_markdown_through() -> None:
    assert connector_markdown("# Title\n\n- item\n") == "# Title\n\n- item\n"


def test_connector_markdown_rejects_json_without_file_content() -> None:
    with pytest.raises(ValueError, match="fileContent"):
        connector_markdown(json.dumps({"files": []}))


def test_normalize_unescapes_punctuation_but_keeps_cell_pipes() -> None:
    text = "10\\\\\\_context and \\*\\*bold\\*\\* and 1abc\\_def-ghi and a \\| b"
    expected = "10_context and **bold** and 1abc_def-ghi and a \\| b\n"
    assert normalize_connector_markdown(text) == expected


def test_normalize_dedents_connector_bullets_so_drive_ids_parse() -> None:
    text = "## Drive IDs\n\n  - Project folder: 1abc\n  - 90\\_LOG: 1\\_log\n"
    normalized = normalize_connector_markdown(text)
    assert "\n- Project folder: 1abc\n" in normalized
    assert instruction_drive_ids(normalized) == {"Project folder": "1abc", "90_LOG": "1_log"}


def test_normalize_drops_end_list_markers_and_trailing_spaces() -> None:
    text = "  - one  \n      \n      - nested  \n\n<!-- end list -->\n\n1.  numbered  \n"
    assert normalize_connector_markdown(text) == "- one\n\n- nested\n\n1.  numbered\n"


def test_normalize_rebuilds_the_index_table_from_a_doc_rendering() -> None:
    text = (
        "## Files\n\n"
        "|  |  |  |  |  |\n"
        "| :-: | :-: | :-: | :-: | :-: |\n"
        "| \\*\\*File\\*\\* | \\*\\*Drive ID\\*\\* | \\*\\*What it contains\\*\\* "
        "| \\*\\*When to read\\*\\* | \\*\\*Owner\\*\\* |\n"
        "| 10\\\\\\_context/Momentum backtest 2026 | TODO-ID | Extract "
        "| when discussing momentum | Ana |\n"
    )
    normalized = normalize_connector_markdown(text)
    assert INDEX_HEADER in normalized
    assert "|  |  |" not in normalized
    assert parse_index(normalized) == [
        IndexRow(
            "10_context/Momentum backtest 2026",
            "TODO-ID",
            "Extract",
            "when discussing momentum",
            "Ana",
        )
    ]


def test_normalize_leaves_a_clean_local_index_unchanged() -> None:
    table = "| File | Drive ID | What it contains | When to read | Owner |\n"
    table += "| --- | --- | --- | --- | --- |\n"
    table += "| 10_context/a.md | 1a | A \\| B | always | Ana |\n"
    assert normalize_connector_markdown(table) == table


@given(
    st.text(
        alphabet=string.ascii_letters + string.digits + string.punctuation + " \t\n",
        max_size=300,
    )
)
def test_normalize_is_idempotent_on_its_own_output(text: str) -> None:
    once = normalize_connector_markdown(text)
    assert normalize_connector_markdown(once) == once


def test_real_instructions_fixture_yields_all_canonical_ids() -> None:
    text = connector_markdown(_fixture("00_INSTRUCTIONS.json"))
    ids = instruction_drive_ids(text)
    assert [ids[label] for label in CANONICAL_LABELS] == [
        "1_project_folder_000000000000000A",
        "1_context_folder_000000000000000B",
        "1_sources_folder_000000000000000C",
        "1_index_doc_000000000000000000000000000000-D",
        "1_log_doc_00000000000000000000000000000000-E",
    ]
    assert missing_canonical_ids(text) == []


def test_real_index_fixture_parses_two_rows_with_placeholders() -> None:
    rows = parse_index(connector_markdown(_fixture("01_INDEX.json")))
    assert [row.file for row in rows] == [
        "10_context/Momentum backtest 2026",
        "20_sources/momentum_backtest_2026.md",
    ]
    assert {row.drive_id for row in rows} == {"TODO-ID"}


def test_plain_md_fixture_unescapes_headings_bullets_and_source() -> None:
    text = connector_markdown(_fixture("pricing_notes.md.json"))
    assert first_heading(text) == "Pricing notes"
    assert source_reference(text) == ("20_sources/momentum_backtest_2026.md", "TODO-ID")
    assert "\n- Plain .md file" in text
    assert "  \n" not in text


def test_probe_fixture_keeps_literal_pipes_and_drops_code_marks() -> None:
    text = connector_markdown(_fixture("zz_format_probe.json"))
    rows = {row.file: row for row in parse_index(text)}
    assert rows["10_context/pipe"].summary == "a | b literal pipe"
    assert rows["10_context/code"].summary == "code_span here"
    assert rows["10_context/bold"].summary == "**bold** word inside"
    assert source_reference(text) == ("20_sources/some_file.pdf", "1abc_def-ghi")
    assert "<!-- end list -->" not in text


def test_source_reference_tolerates_the_line_docs_joins_with_extracted() -> None:
    text = connector_markdown(_fixture("momentum_extract.json"))
    assert source_reference(text) == (
        "20_sources/momentum_backtest_2026.md",
        "1_momentum_md_00000000000000000-I",
    )


def test_source_reference_without_id_but_with_joined_tail() -> None:
    line = "Source: 20_sources/a b.pdf Extracted: 2026-09-13 by Ana\n"
    assert source_reference(line) == ("20_sources/a b.pdf", None)


def test_parse_listing_reads_a_saved_search_result() -> None:
    entries = parse_listing(_fixture("10_context.json"))
    assert entries == [
        DriveEntry(
            "1_momentum_doc_000000000000000000000000000-G",
            "Momentum backtest 2026",
            "application/vnd.google-apps.document",
            "1_context_folder_000000000000000B",
            None,
        ),
        DriveEntry(
            "1_pricing_md_000000000000000000-H",
            "pricing_notes.md",
            "text/markdown",
            "1_context_folder_000000000000000B",
            None,
        ),
    ]
    assert not entries[0].is_folder


def test_parse_listing_accepts_a_bare_list_and_the_name_key() -> None:
    raw = json.dumps(
        [{"id": "1x", "name": "Doc", "mimeType": "application/vnd.google-apps.folder"}]
    )
    (entry,) = parse_listing(raw)
    assert entry.title == "Doc"
    assert entry.parent_id is None
    assert entry.is_folder


def test_parse_listing_reads_a_path_csv() -> None:
    entries = parse_listing("path,drive_id\n10_context/topic.md,1abc\n20_sources/source.pdf,\n")
    assert entries == [
        DriveEntry("1abc", "topic.md", "", None, "10_context/topic.md"),
        DriveEntry("", "source.pdf", "", None, "20_sources/source.pdf"),
    ]


@pytest.mark.parametrize(
    "raw",
    [
        '{"files": [{"title": "no id"}]}',
        '{"files": "nope"}',
        "[1, 2]",
        "path\nx\n",
        "{not json",
    ],
)
def test_parse_listing_rejects_malformed_input(raw: str) -> None:
    with pytest.raises(ValueError):
        parse_listing(raw)


def test_parse_drive_csv_normalizes_backslashes_and_skips_blank_paths() -> None:
    assert parse_drive_csv("path,drive_id\n10_context\\a.md,1a\n,1b\n") == {"10_context/a.md": "1a"}


def test_missing_canonical_ids_is_none_without_the_section() -> None:
    assert missing_canonical_ids("# P\n\n- Project folder: 1a\n") is None


def test_missing_canonical_ids_lists_placeholders_and_blanks() -> None:
    text = (
        "## Drive IDs\n\n- Project folder: TODO-ID\n- 10_context folder: 1c\n"
        "- 20_sources folder: 1s\n- 01_INDEX: 1i\n- 90_LOG:\n"
    )
    assert missing_canonical_ids(text) == ["Project folder", "90_LOG"]


def test_canonical_id_collisions_only_involve_canonical_labels() -> None:
    text = (
        "## Drive IDs\n\n- Project folder: 1p\n- 10_context folder: 1c\n"
        "- 20_sources folder: 1s\n- 01_INDEX: 1i\n- 90_LOG: 1i\n"
    )
    rows = [
        IndexRow("10_context/a.md", "1c", "A", "always", "Ana"),
        IndexRow("10_context/b.md", "same", "B", "always", "Ana"),
        IndexRow("10_context/c.md", "same", "C", "always", "Ana"),
    ]
    assert canonical_id_collisions(text, rows) == [
        ("1c", ["10_context/a.md", "00_INSTRUCTIONS.md:10_context folder"]),
        ("1i", ["00_INSTRUCTIONS.md:01_INDEX", "00_INSTRUCTIONS.md:90_LOG"]),
    ]
