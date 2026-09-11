"""Tests for scripts/build_index.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from build_index import EXIT_OK, EXIT_USAGE, main, merge, scan, scan_files
from common import CONTEXT_DIR, ID_PLACEHOLDER, INDEX_FILE, SOURCES_DIR, IndexRow, parse_index


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
