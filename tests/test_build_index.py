"""Tests for scripts/build_index.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from build_index import EXIT_OK, EXIT_USAGE, duplicate_files, main, merge, scan
from common import (
    CONTEXT_DIR,
    ID_PLACEHOLDER,
    INDEX_FILE,
    SOURCES_DIR,
    IndexRow,
    parse_index,
    render_index_table,
    scan_files,
)


@pytest.fixture()
def tree(tmp_path: Path) -> Path:
    (tmp_path / CONTEXT_DIR).mkdir()
    (tmp_path / SOURCES_DIR).mkdir()
    (tmp_path / CONTEXT_DIR / ".gitkeep").write_text("", encoding="utf-8")
    (tmp_path / CONTEXT_DIR / "pricing.md").write_text("# Pricing model\n\nbody", encoding="utf-8")
    (tmp_path / SOURCES_DIR / "contract.pdf").write_bytes(b"%PDF-1.4 fake")
    (tmp_path / INDEX_FILE).write_text(
        "# Index\n\n## Files\n\n"
        "| File | Drive ID | What it contains | When to read | Owner |\n"
        "| --- | --- | --- | --- | --- |\n",
        encoding="utf-8",
    )
    return tmp_path


def test_scan_files_skips_dotfiles_and_sorts(tree: Path) -> None:
    assert scan_files(tree) == ["10_context/pricing.md", "20_sources/contract.pdf"]


def test_scan_uses_first_heading_for_markdown(tree: Path) -> None:
    rows = scan(tree)
    assert rows == [
        IndexRow("10_context/pricing.md", ID_PLACEHOLDER, "Pricing model", "", ""),
        IndexRow("20_sources/contract.pdf", ID_PLACEHOLDER, "", "", ""),
    ]


def test_merge_keeps_human_fields_and_drops_stale_rows() -> None:
    existing = [
        IndexRow("10_context/pricing.md", "id123", "Hand-written summary", "always", "me"),
        IndexRow("10_context/gone.md", "id999", "Deleted", "never", "me"),
    ]
    scanned = [
        IndexRow("10_context/pricing.md", ID_PLACEHOLDER, "Pricing model", "", ""),
        IndexRow("20_sources/new.pdf", ID_PLACEHOLDER, "", "", ""),
    ]
    assert merge(existing, scanned) == [
        IndexRow("10_context/pricing.md", "id123", "Hand-written summary", "always", "me"),
        IndexRow("20_sources/new.pdf", ID_PLACEHOLDER, "", "", ""),
    ]


def test_merge_fills_empty_existing_fields_from_scan() -> None:
    existing = [IndexRow("10_context/pricing.md", "", "", "always", "")]
    scanned = [IndexRow("10_context/pricing.md", ID_PLACEHOLDER, "Pricing model", "", "")]
    assert merge(existing, scanned) == [
        IndexRow("10_context/pricing.md", ID_PLACEHOLDER, "Pricing model", "always", "")
    ]


def test_main_prints_table_without_write(tree: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--root", str(tree)]) == EXIT_OK
    out = capsys.readouterr().out
    assert "| 10_context/pricing.md | TODO-ID | Pricing model |  |  |" in out
    assert parse_index((tree / INDEX_FILE).read_text(encoding="utf-8")) == []


def test_main_write_updates_index_in_place(tree: Path) -> None:
    assert main(["--root", str(tree), "--write"]) == EXIT_OK
    text = (tree / INDEX_FILE).read_text(encoding="utf-8")
    assert text.startswith("# Index\n\n## Files\n\n")
    assert parse_index(text) == scan(tree)


def test_main_missing_index_is_usage_error(tmp_path: Path) -> None:
    assert main(["--root", str(tmp_path)]) == EXIT_USAGE


def test_exit_constants_are_the_literal_codes() -> None:
    assert (EXIT_OK, EXIT_USAGE) == (0, 2)


def test_main_missing_context_dir_is_usage_error(
    tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tree / CONTEXT_DIR / ".gitkeep").unlink()
    (tree / CONTEXT_DIR / "pricing.md").unlink()
    (tree / CONTEXT_DIR).rmdir()
    assert main(["--root", str(tree)]) == 2
    err = capsys.readouterr().err
    assert CONTEXT_DIR in err
    assert "not found" in err


def test_main_write_missing_sources_dir_is_usage_error(
    tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tree / SOURCES_DIR / "contract.pdf").unlink()
    (tree / SOURCES_DIR).rmdir()
    assert main(["--root", str(tree), "--write"]) == 2
    assert SOURCES_DIR in capsys.readouterr().err
    assert parse_index((tree / INDEX_FILE).read_text(encoding="utf-8")) == []


def test_main_write_reports_removed_stale_rows(
    tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tree / INDEX_FILE).write_text(
        "# Index\n\n## Files\n\n"
        + render_index_table(
            [
                IndexRow("10_context/pricing.md", "id1", "Kept", "always", "me"),
                IndexRow("10_context/gone.md", "id2", "Vanished", "never", "me"),
                IndexRow("20_sources/also-gone.pdf", "id3", "Vanished too", "never", "me"),
            ]
        ),
        encoding="utf-8",
    )
    assert main(["--root", str(tree), "--write", "--allow-drop"]) == 0
    err = capsys.readouterr().err
    assert "removed 2 stale row(s)" in err
    assert "10_context/gone.md" in err
    assert "20_sources/also-gone.pdf" in err
    assert [row.file for row in parse_index((tree / INDEX_FILE).read_text(encoding="utf-8"))] == [
        "10_context/pricing.md",
        "20_sources/contract.pdf",
    ]


def test_main_write_stays_quiet_when_nothing_is_dropped(
    tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--root", str(tree), "--write"]) == 0
    assert "stale" not in capsys.readouterr().err


def test_main_write_appends_a_table_when_the_index_has_none(tree: Path) -> None:
    (tree / INDEX_FILE).write_text("# Index\n\nNo table yet.\n", encoding="utf-8")
    assert main(["--root", str(tree), "--write"]) == 0
    text = (tree / INDEX_FILE).read_text(encoding="utf-8")
    assert text.startswith("# Index\n\nNo table yet.\n")
    assert parse_index(text) == scan(tree)


def test_scan_gives_an_empty_summary_for_an_undecodable_file(tree: Path) -> None:
    (tree / CONTEXT_DIR / "binary.md").write_bytes(b"\xff\xfe\x00broken")
    (tree / CONTEXT_DIR / "latin.txt").write_bytes("cafe\xe9\n".encode("latin-1"))
    rows = {row.file: row.summary for row in scan(tree)}
    assert rows["10_context/binary.md"] == ""
    assert rows["10_context/latin.txt"] == ""


CP1252_INDEX = "# \xcdndice\n".encode("cp1252")


def test_main_non_utf8_index_is_usage_error(tree: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tree / INDEX_FILE).write_bytes(CP1252_INDEX)
    assert main(["--root", str(tree)]) == 2
    assert "is not readable as UTF-8 text" in capsys.readouterr().err


def test_main_write_non_utf8_index_is_usage_error_and_keeps_the_file(
    tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tree / INDEX_FILE).write_bytes(CP1252_INDEX)
    assert main(["--root", str(tree), "--write"]) == 2
    assert "is not readable as UTF-8 text" in capsys.readouterr().err
    assert (tree / INDEX_FILE).read_bytes() == CP1252_INDEX


def test_duplicate_files_lists_repeated_rows_once() -> None:
    existing = [
        IndexRow("10_context/pricing.md", "id1", "First", "always", "me"),
        IndexRow("10_context/pricing.md", "id2", "Second", "never", "you"),
        IndexRow("10_context/pricing.md", "id3", "Third", "never", "you"),
        IndexRow("20_sources/contract.pdf", "id4", "Only once", "detail", "me"),
    ]
    assert duplicate_files(existing) == ["10_context/pricing.md"]


def test_duplicate_files_is_empty_without_repeats() -> None:
    assert duplicate_files([IndexRow("10_context/a.md", "id1", "S", "W", "O")]) == []


def test_merge_keeps_the_first_of_two_rows_for_the_same_file() -> None:
    existing = [
        IndexRow("10_context/pricing.md", "id1", "First", "always", "me"),
        IndexRow("10_context/pricing.md", "id2", "Second", "never", "you"),
    ]
    scanned = [IndexRow("10_context/pricing.md", ID_PLACEHOLDER, "Pricing model", "", "")]
    assert merge(existing, scanned) == [
        IndexRow("10_context/pricing.md", "id1", "First", "always", "me")
    ]


def test_main_warns_about_duplicate_rows(tree: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tree / INDEX_FILE).write_text(
        "# Index\n\n## Files\n\n"
        + render_index_table(
            [
                IndexRow("10_context/pricing.md", "id1", "First", "always", "me"),
                IndexRow("10_context/pricing.md", "id2", "Second", "never", "you"),
                IndexRow("20_sources/contract.pdf", "id3", "Contract", "detail", "me"),
            ]
        ),
        encoding="utf-8",
    )
    assert main(["--root", str(tree), "--write"]) == 0
    assert (
        "warning: duplicate index rows for 10_context/pricing.md (kept the first)"
        in capsys.readouterr().err
    )
    rows = parse_index((tree / INDEX_FILE).read_text(encoding="utf-8"))
    assert rows == [
        IndexRow("10_context/pricing.md", "id1", "First", "always", "me"),
        IndexRow("20_sources/contract.pdf", "id3", "Contract", "detail", "me"),
    ]
