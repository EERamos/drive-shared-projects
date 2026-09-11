"""Tests for scripts/common.py."""

from __future__ import annotations

from hypothesis import given
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
    render_index_table,
    replace_index_table,
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


@given(
    st.lists(
        st.tuples(
            st.text(alphabet="abc/_.", min_size=1, max_size=20),
            st.text(alphabet="xyz0123", min_size=1, max_size=10),
            st.text(alphabet="def |g", min_size=0, max_size=20),
            st.text(alphabet="hij", min_size=0, max_size=8),
            st.text(alphabet="klm", min_size=0, max_size=8),
        ),
        max_size=6,
    )
)
def test_render_then_parse_roundtrip(cells: list[tuple[str, str, str, str, str]]) -> None:
    rows = [IndexRow(*[c.strip() for c in tup]) for tup in cells]
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
    assert out.endswith("| --- | --- | --- | --- | --- |\n")


def test_first_heading() -> None:
    assert first_heading("intro\n## Title here\n# later") == "Title here"
    assert first_heading("no headings") is None


def test_normalize_stem_strips_prefix_and_extension() -> None:
    assert normalize_stem("10_context/03_Market Data.md") == "market-data"
    assert normalize_stem("20_sources/market_data.pdf") == "market-data"


def test_fill_template_replaces_all_known_placeholders() -> None:
    out = fill_template("{{A}} and {{B}} and {{A}}", {"A": "1", "B": "2"})
    assert out == "1 and 2 and 1"


def test_fill_template_leaves_unknown_placeholders() -> None:
    assert fill_template("{{A}} {{Z}}", {"A": "1"}) == "1 {{Z}}"
