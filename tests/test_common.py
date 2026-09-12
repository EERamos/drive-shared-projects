"""Tests for scripts/common.py."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from common import (
    CONTEXT_DIR,
    ID_PLACEHOLDER,
    INDEX_FILE,
    INDEX_HEADER,
    INDEX_SEPARATOR,
    INSTRUCTIONS_FILE,
    LOG_FILE,
    SOURCES_DIR,
    TEXT_SUFFIXES,
    ExitCode,
    Format,
    IndexRow,
    Mode,
    fill_template,
    first_heading,
    missing_project_paths,
    parse_args_or_exit,
    parse_index,
    read_index_or_error,
    read_text,
    relative_posix,
    render_index_table,
    replace_index_table,
    scan_files,
    write_text,
)


def test_mode_and_format_values() -> None:
    assert {m.value for m in Mode} == {"solo", "duo", "group"}
    assert {f.value for f in Format} == {"docs", "md"}


def test_index_row_to_markdown_escapes_pipes() -> None:
    row = IndexRow("10_context/a.md", ID_PLACEHOLDER, "has | pipe", "always", "me")
    assert row.to_markdown() == "| 10_context/a.md | TODO-ID | has \\| pipe | always | me |"


def test_parse_index_skips_header_and_separator() -> None:
    text = (
        "# Index\n\n"
        "| File | Drive ID | What it contains | When to read | Owner |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 10_context/a.md | abc123 | Summary A | always | me |\n"
        "| 20_sources/b.pdf | TODO-ID | Original B | detail | you |\n"
    )
    rows = parse_index(text)
    assert rows == [
        IndexRow("10_context/a.md", "abc123", "Summary A", "always", "me"),
        IndexRow("20_sources/b.pdf", "TODO-ID", "Original B", "detail", "you"),
    ]


def test_parse_index_ignores_tables_with_other_widths() -> None:
    text = "| a | b |\n| --- | --- |\n| 1 | 2 |\n"
    assert parse_index(text) == []


_LEGEND_TABLE = "| Column | Meaning |\n| --- | --- |\n| File | Path in the project |\n"
_INDEX_TABLE = (
    "| File | Drive ID | What it contains | When to read | Owner |\n"
    "| --- | --- | --- | --- | --- |\n"
    "| 10_context/a.md | abc123 | Summary A | always | me |\n"
)
_SECOND_TABLE = (
    "| Other | Five | Column | Table | Here |\n"
    "| --- | --- | --- | --- | --- |\n"
    "| x1 | x2 | x3 | x4 | x5 |\n"
)
_INDEX_ROW = IndexRow("10_context/a.md", "abc123", "Summary A", "always", "me")
_NEW_ROW = IndexRow("10_context/b.md", "id2", "Summary B", "never", "you")


def test_parse_index_skips_a_narrower_table_before_the_index() -> None:
    text = "# Index\n\n" + _LEGEND_TABLE + "\n" + _INDEX_TABLE
    assert parse_index(text) == [_INDEX_ROW]


def test_replace_index_table_keeps_a_narrower_table_before_the_index() -> None:
    text = "# Index\n\n" + _LEGEND_TABLE + "\n" + _INDEX_TABLE
    out = replace_index_table(text, render_index_table([_NEW_ROW]))
    assert _LEGEND_TABLE in out
    assert _NEW_ROW.to_markdown() in out
    assert _INDEX_ROW.to_markdown() not in out


def test_parse_index_ignores_a_second_five_column_table() -> None:
    text = _INDEX_TABLE + "\n" + _SECOND_TABLE
    assert parse_index(text) == [_INDEX_ROW]


def test_replace_index_table_leaves_a_second_five_column_table_untouched() -> None:
    text = _INDEX_TABLE + "\n" + _SECOND_TABLE
    out = replace_index_table(text, render_index_table([_NEW_ROW]))
    assert _SECOND_TABLE in out
    assert _NEW_ROW.to_markdown() in out
    assert _INDEX_ROW.to_markdown() not in out


_CELL = st.text(alphabet=st.characters(blacklist_characters="\n\r"), max_size=20)


@given(st.lists(st.tuples(_CELL, _CELL, _CELL, _CELL, _CELL), max_size=6))
def test_render_then_parse_roundtrip(cells: list[tuple[str, str, str, str, str]]) -> None:
    rows = [IndexRow(*[c.strip() for c in tup]) for tup in cells]
    for row in rows:
        assume(row.file != "File")
        assume(not (row.file != "" and set(row.file) <= {"-", ":"}))
    assert parse_index(render_index_table(rows)) == rows


def test_replace_index_table_replaces_first_table_block() -> None:
    text = (
        "# Index\n\nIntro.\n\n"
        "| File | Drive ID | What it contains | When to read | Owner |\n"
        "| --- | --- | --- | --- | --- |\n"
        "\nTrailer.\n"
    )
    new_table = render_index_table([IndexRow("10_context/a.md", "id1", "S", "W", "O")])
    out = replace_index_table(text, new_table)
    assert "| 10_context/a.md | id1 | S | W | O |" in out
    assert out.startswith("# Index\n\nIntro.\n\n")
    assert out.endswith("\nTrailer.\n")


def test_replace_index_table_appends_when_no_table() -> None:
    out = replace_index_table("# Index\n", render_index_table([]))
    assert out.startswith("# Index\n\n")
    assert out.endswith("| --- | --- | --- | --- | --- |\n")


def test_replace_index_table_appends_when_text_has_no_trailing_newline() -> None:
    out = replace_index_table("# Index", render_index_table([]))
    assert out.startswith("# Index\n\n")
    assert out.endswith("| --- | --- | --- | --- | --- |\n")


def test_first_heading() -> None:
    assert first_heading("intro\n## Title here\n# later") == "Title here"
    assert first_heading("no headings") is None


def test_first_heading_ignores_a_bare_hash_line() -> None:
    assert first_heading("#\n# real") == "real"


def test_fill_template_replaces_all_known_placeholders() -> None:
    out = fill_template("{{A}} and {{B}} and {{A}}", {"A": "1", "B": "2"})
    assert out == "1 and 2 and 1"


def test_fill_template_leaves_unknown_placeholders() -> None:
    assert fill_template("{{A}} {{Z}}", {"A": "1"}) == "1 {{Z}}"


def test_write_text_writes_lf_only(tmp_path: Path) -> None:
    target = tmp_path / "out.md"
    text = "first\nsecond\n"
    write_text(target, text)
    assert b"\r\n" not in target.read_bytes()
    assert read_text(target) == text


def test_relative_posix_uses_forward_slashes(tmp_path: Path) -> None:
    assert relative_posix(tmp_path, tmp_path / "10_context" / "a.md") == "10_context/a.md"


def test_exit_code_values_are_the_literal_codes() -> None:
    assert (ExitCode.OK, ExitCode.FINDINGS, ExitCode.USAGE) == (0, 1, 2)


def test_text_suffixes_holds_the_readable_extensions() -> None:
    assert ".md" in TEXT_SUFFIXES
    assert ".txt" in TEXT_SUFFIXES
    assert ".pdf" not in TEXT_SUFFIXES


def test_scan_files_finds_nested_files_with_forward_slashes(tmp_path: Path) -> None:
    nested = tmp_path / CONTEXT_DIR / "sub" / "deeper"
    nested.mkdir(parents=True)
    (nested / "note.md").write_text("# Note\n", encoding="utf-8")
    (tmp_path / CONTEXT_DIR / ".gitkeep").write_text("", encoding="utf-8")
    (tmp_path / SOURCES_DIR).mkdir()
    (tmp_path / SOURCES_DIR / "a.pdf").write_bytes(b"%PDF")
    assert scan_files(tmp_path) == ["10_context/sub/deeper/note.md", "20_sources/a.pdf"]


def test_scan_files_tolerates_missing_directories(tmp_path: Path) -> None:
    assert scan_files(tmp_path) == []


def _demo_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="demo")
    parser.add_argument("--name", required=True)
    return parser


def test_parse_args_or_exit_returns_the_namespace() -> None:
    parsed = parse_args_or_exit(_demo_parser(), ["--name", "x"])
    assert isinstance(parsed, argparse.Namespace)
    assert parsed.name == "x"


def test_parse_args_or_exit_returns_usage_code_on_bad_arguments() -> None:
    assert parse_args_or_exit(_demo_parser(), []) == 2


def test_parse_args_or_exit_returns_ok_code_on_help() -> None:
    assert parse_args_or_exit(_demo_parser(), ["--help"]) == 0


def _table(rows: str) -> str:
    return INDEX_HEADER + "\n" + INDEX_SEPARATOR + "\n" + rows


def test_parse_index_prefers_the_header_anchored_table() -> None:
    text = (
        "# Doc\n\n"
        "| a | b | c | d | e |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 1 | 2 | 3 | 4 | 5 |\n\n"
        "## Files\n\n" + _table("| 10_context/a.md | id1 | S | W | O |\n")
    )
    assert parse_index(text) == [IndexRow("10_context/a.md", "id1", "S", "W", "O")]


def test_replace_index_table_leaves_an_unrelated_five_column_table_intact() -> None:
    text = (
        "# Doc\n\n"
        "| a | b | c | d | e |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 1 | 2 | 3 | 4 | 5 |\n\n"
        "## Files\n\n" + _table("| 10_context/a.md | id1 | S | W | O |\n")
    )
    new_table = render_index_table([IndexRow("10_context/b.md", "id2", "S2", "W2", "O2")])
    out = replace_index_table(text, new_table)
    assert "| 1 | 2 | 3 | 4 | 5 |" in out
    assert "| a | b | c | d | e |" in out
    assert "10_context/a.md" not in out
    assert "| 10_context/b.md | id2 | S2 | W2 | O2 |" in out
    assert out.startswith("# Doc\n\n")


CP1252_INDEX = "Resumen del a\xf1o\n".encode("cp1252")


def test_exit_code_refused_is_an_alias_of_findings() -> None:
    assert (ExitCode.REFUSED, ExitCode.FINDINGS) == (1, 1)
    assert ExitCode(1).name == "FINDINGS"
    assert list(ExitCode) == [ExitCode.OK, ExitCode.FINDINGS, ExitCode.USAGE]


def test_read_index_or_error_returns_the_text(tmp_path: Path) -> None:
    path = tmp_path / INDEX_FILE
    path.write_text("# Index\n", encoding="utf-8")
    assert read_index_or_error(path) == "# Index\n"


def test_read_index_or_error_reports_a_non_utf8_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / INDEX_FILE
    path.write_bytes(CP1252_INDEX)
    assert read_index_or_error(path) == 2
    err = capsys.readouterr().err
    assert "is not readable as UTF-8 text" in err
    assert INDEX_FILE in err


def test_read_index_or_error_reports_a_missing_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert read_index_or_error(tmp_path / INDEX_FILE) == 2
    assert "is not readable as UTF-8 text" in capsys.readouterr().err


def test_missing_project_paths_is_empty_for_a_complete_tree(tmp_path: Path) -> None:
    (tmp_path / INSTRUCTIONS_FILE).write_text("# Instructions\n", encoding="utf-8")
    (tmp_path / INDEX_FILE).write_text("# Index\n", encoding="utf-8")
    (tmp_path / LOG_FILE).write_text("# Log\n", encoding="utf-8")
    (tmp_path / CONTEXT_DIR).mkdir()
    (tmp_path / SOURCES_DIR).mkdir()
    assert missing_project_paths(tmp_path) == []


def test_missing_project_paths_lists_every_absent_requirement(tmp_path: Path) -> None:
    assert [p.name for p in missing_project_paths(tmp_path)] == [
        INSTRUCTIONS_FILE,
        INDEX_FILE,
        LOG_FILE,
        CONTEXT_DIR,
        SOURCES_DIR,
    ]


def test_missing_project_paths_lists_only_the_absent_ones(tmp_path: Path) -> None:
    (tmp_path / INSTRUCTIONS_FILE).write_text("# Instructions\n", encoding="utf-8")
    (tmp_path / INDEX_FILE).write_text("# Index\n", encoding="utf-8")
    (tmp_path / CONTEXT_DIR).mkdir()
    assert [p.name for p in missing_project_paths(tmp_path)] == [LOG_FILE, SOURCES_DIR]
