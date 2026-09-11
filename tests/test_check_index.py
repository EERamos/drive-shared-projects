"""Tests for scripts/check_index.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from check_index import EXIT_FINDINGS, EXIT_OK, EXIT_USAGE, Finding, FindingKind, check, main
from common import CONTEXT_DIR, INDEX_FILE, SOURCES_DIR, IndexRow, render_index_table

INDEX_HEAD = "# Index\n\n## Files\n\n"


def _write_index(root: Path, rows: list[IndexRow]) -> None:
    (root / INDEX_FILE).write_text(INDEX_HEAD + render_index_table(rows), encoding="utf-8")


@pytest.fixture()
def clean_tree(tmp_path: Path) -> Path:
    (tmp_path / CONTEXT_DIR).mkdir()
    (tmp_path / SOURCES_DIR).mkdir()
    (tmp_path / CONTEXT_DIR / "pricing.md").write_text(
        "# Pricing\n\nSource: 20_sources/pricing.pdf (Drive ID: abc)\n", encoding="utf-8"
    )
    (tmp_path / SOURCES_DIR / "pricing.pdf").write_bytes(b"%PDF fake")
    _write_index(
        tmp_path,
        [
            IndexRow("10_context/pricing.md", "id1", "Pricing extract", "always", "me"),
            IndexRow("20_sources/pricing.pdf", "abc", "Pricing original", "detail", "me"),
        ],
    )
    return tmp_path


def test_clean_tree_has_no_findings(clean_tree: Path) -> None:
    assert check(clean_tree) == []


def test_missing_row(clean_tree: Path) -> None:
    (clean_tree / CONTEXT_DIR / "risk.md").write_text("# Risk\n", encoding="utf-8")
    kinds = {f.kind for f in check(clean_tree)}
    assert kinds == {FindingKind.MISSING_ROW}
    assert any(f.path == "10_context/risk.md" for f in check(clean_tree))


def test_stale_row(clean_tree: Path) -> None:
    (clean_tree / SOURCES_DIR / "pricing.pdf").unlink()
    findings = check(clean_tree)
    assert findings == [
        Finding(FindingKind.STALE_ROW, "20_sources/pricing.pdf", "row exists but file is missing")
    ]


def test_too_large_only_applies_to_context(clean_tree: Path) -> None:
    (clean_tree / CONTEXT_DIR / "pricing.md").write_text(
        "# Pricing\n\nSource: x\n" + "a" * 60, encoding="utf-8"
    )
    (clean_tree / SOURCES_DIR / "pricing.pdf").write_bytes(b"x" * 500)
    findings = check(clean_tree, max_chars=50)
    assert [f.kind for f in findings] == [FindingKind.TOO_LARGE]
    assert findings[0].path == "10_context/pricing.md"


def test_duplicate_topic_when_extract_lacks_source_line(clean_tree: Path) -> None:
    (clean_tree / CONTEXT_DIR / "pricing.md").write_text(
        "# Pricing\n\nno source line\n", encoding="utf-8"
    )
    findings = check(clean_tree)
    assert [f.kind for f in findings] == [FindingKind.DUPLICATE_TOPIC]
    assert findings[0].path == "10_context/pricing.md"
    assert "20_sources/pricing.pdf" in findings[0].detail


def test_main_exit_codes(
    clean_tree: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--root", str(clean_tree)]) == EXIT_OK
    assert "OK" in capsys.readouterr().out
    (clean_tree / CONTEXT_DIR / "extra.md").write_text("# Extra\n", encoding="utf-8")
    assert main(["--root", str(clean_tree)]) == EXIT_FINDINGS
    assert "MISSING_ROW 10_context/extra.md" in capsys.readouterr().out
    empty = tmp_path / "empty"
    empty.mkdir()
    assert main(["--root", str(empty)]) == EXIT_USAGE
