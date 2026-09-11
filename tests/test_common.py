"""Tests for scripts/common.py."""

from __future__ import annotations

from pathlib import Path

from hypothesis import assume, given
from hypothesis import strategies as st

from common import (
    ID_PLACEHOLDER,
    Format,
    IndexRow,
    Mode,
    fill_template,
    first_heading,
    normalize_stem,
    parse_index,
    read_text,
    relative_posix,
    render_index_table,
    replace_index_table,
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


def test_normalize_stem_strips_prefix_and_extension() -> None:
    assert normalize_stem("10_context/03_Market Data.md") == "market-data"
    assert normalize_stem("20_sources/market_data.pdf") == "market-data"


def test_normalize_stem_folds_accents() -> None:
    assert normalize_stem("20_sources/Análisis.pdf") == "analisis"
    assert normalize_stem("10_context/Año Fiscal.md") == "ano-fiscal"


def test_normalize_stem_keeps_all_digit_stems_distinct() -> None:
    assert normalize_stem("20_sources/2024.pdf") == "2024"
    assert normalize_stem("20_sources/2025.pdf") == "2025"


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
