"""Tests for scripts/check_index.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from check_index import EXIT_FINDINGS, EXIT_OK, EXIT_USAGE, Finding, FindingKind, check, main
from common import (
    CONTEXT_DIR,
    INDEX_FILE,
    INSTRUCTIONS_FILE,
    LOG_FILE,
    SOURCES_DIR,
    IndexRow,
    render_index_table,
)

INDEX_HEAD = "# Index\n\n## Files\n\n"
INSTRUCTIONS_TEXT = (
    "# Project\n\n## Drive IDs\n\n"
    "- Project folder: project-folder-id\n"
    "- 10_context folder: context-folder-id\n"
    "- 20_sources folder: sources-folder-id\n"
    "- 01_INDEX: index-file-id\n"
    "- 90_LOG: log-file-id\n"
)


def _write_index(root: Path, rows: list[IndexRow]) -> None:
    (root / INDEX_FILE).write_text(INDEX_HEAD + render_index_table(rows), encoding="utf-8")


@pytest.fixture()
def clean_tree(tmp_path: Path) -> Path:
    (tmp_path / CONTEXT_DIR).mkdir()
    (tmp_path / SOURCES_DIR).mkdir()
    (tmp_path / INSTRUCTIONS_FILE).write_text(INSTRUCTIONS_TEXT, encoding="utf-8")
    (tmp_path / LOG_FILE).write_text("# Log\n", encoding="utf-8")
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
    assert [f.kind for f in findings] == [
        FindingKind.STALE_ROW,
        FindingKind.INVALID_SOURCE_REFERENCE,
    ]
    assert findings[0] == Finding(
        FindingKind.STALE_ROW,
        "20_sources/pricing.pdf",
        "row exists but file is missing",
    )
    assert findings[1].path == "10_context/pricing.md"
    assert "Source path does not exist" in findings[1].detail


def test_too_large_only_applies_to_context(clean_tree: Path) -> None:
    (clean_tree / CONTEXT_DIR / "pricing.md").write_text(
        "# Pricing\n\nSource: 20_sources/pricing.pdf (Drive ID: abc)\n" + "a" * 60,
        encoding="utf-8",
    )
    (clean_tree / SOURCES_DIR / "pricing.pdf").write_bytes(b"x" * 500)
    findings = check(clean_tree, max_chars=50)
    assert [f.kind for f in findings] == [FindingKind.TOO_LARGE]
    assert findings[0].path == "10_context/pricing.md"


def test_an_extract_without_a_source_line_is_not_a_finding(clean_tree: Path) -> None:
    (clean_tree / CONTEXT_DIR / "pricing.md").write_text(
        "# Pricing\n\nno source line\n", encoding="utf-8"
    )
    assert check(clean_tree) == []
    assert not hasattr(FindingKind, "DUPLICATE_TOPIC")


def test_main_exit_codes(
    clean_tree: Path,
    tmp_path_factory: pytest.TempPathFactory,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["--root", str(clean_tree)]) == EXIT_OK
    assert "OK" in capsys.readouterr().out
    (clean_tree / CONTEXT_DIR / "extra.md").write_text("# Extra\n", encoding="utf-8")
    assert main(["--root", str(clean_tree)]) == EXIT_FINDINGS
    assert "MISSING_ROW 10_context/extra.md" in capsys.readouterr().out
    empty = tmp_path_factory.mktemp("empty")
    assert main(["--root", str(empty)]) == EXIT_USAGE


def test_main_exit_codes_are_the_literal_codes(
    clean_tree: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    assert (EXIT_OK, EXIT_FINDINGS, EXIT_USAGE) == (0, 1, 2)
    assert main(["--root", str(clean_tree)]) == 0
    (clean_tree / CONTEXT_DIR / "extra.md").write_text("# Extra\n", encoding="utf-8")
    assert main(["--root", str(clean_tree)]) == 1
    assert main(["--root", str(tmp_path_factory.mktemp("nothing"))]) == 2


def test_unreadable_latin_1_file_is_reported(clean_tree: Path) -> None:
    (clean_tree / CONTEXT_DIR / "notes.txt").write_bytes("cafe\xe9 con leche\n".encode("latin-1"))
    _write_index(
        clean_tree,
        [
            IndexRow("10_context/notes.txt", "id2", "Notes", "always", "me"),
            IndexRow("10_context/pricing.md", "id1", "Pricing extract", "always", "me"),
            IndexRow("20_sources/pricing.pdf", "abc", "Pricing original", "detail", "me"),
        ],
    )
    findings = check(clean_tree)
    assert [f.kind for f in findings] == [FindingKind.UNREADABLE]
    assert findings[0].path == "10_context/notes.txt"
    assert findings[0].detail.startswith("UnicodeDecodeError: ")


def test_unreadable_binary_markdown_is_reported_not_raised(clean_tree: Path) -> None:
    (clean_tree / CONTEXT_DIR / "binary.md").write_bytes(b"\xff\xfe\x00\x01broken")
    _write_index(
        clean_tree,
        [
            IndexRow("10_context/binary.md", "id2", "Binary", "never", "me"),
            IndexRow("10_context/pricing.md", "id1", "Pricing extract", "always", "me"),
            IndexRow("20_sources/pricing.pdf", "abc", "Pricing original", "detail", "me"),
        ],
    )
    findings = check(clean_tree)
    assert [f.kind for f in findings] == [FindingKind.UNREADABLE]
    assert "UnicodeDecodeError" in findings[0].detail


def test_size_cap_applies_to_every_context_file(clean_tree: Path) -> None:
    (clean_tree / CONTEXT_DIR / "table.csv").write_text("a,b\n" * 40, encoding="utf-8")
    _write_index(
        clean_tree,
        [
            IndexRow("10_context/pricing.md", "id1", "Pricing extract", "always", "me"),
            IndexRow("10_context/table.csv", "id2", "A table", "detail", "me"),
            IndexRow("20_sources/pricing.pdf", "abc", "Pricing original", "detail", "me"),
        ],
    )
    findings = check(clean_tree, max_chars=100)
    assert [f.kind for f in findings] == [FindingKind.TOO_LARGE]
    assert findings[0].path == "10_context/table.csv"


def test_duplicate_row(clean_tree: Path) -> None:
    _write_index(
        clean_tree,
        [
            IndexRow("10_context/pricing.md", "id1", "Pricing extract", "always", "me"),
            IndexRow("10_context/pricing.md", "id1", "Pricing extract again", "always", "you"),
            IndexRow("20_sources/pricing.pdf", "abc", "Pricing original", "detail", "me"),
        ],
    )
    findings = check(clean_tree)
    assert findings == [
        Finding(FindingKind.DUPLICATE_ROW, "10_context/pricing.md", "listed 2 times")
    ]


def test_duplicate_row_of_a_missing_file_is_reported_once_as_stale(clean_tree: Path) -> None:
    _write_index(
        clean_tree,
        [
            IndexRow("10_context/gone.md", "id9", "Gone", "never", "me"),
            IndexRow("10_context/gone.md", "id9", "Gone twice", "never", "me"),
            IndexRow("10_context/pricing.md", "id1", "Pricing extract", "always", "me"),
            IndexRow("20_sources/pricing.pdf", "abc", "Pricing original", "detail", "me"),
        ],
    )
    kinds = [f.kind for f in check(clean_tree)]
    assert kinds.count(FindingKind.STALE_ROW) == 1
    assert kinds.count(FindingKind.DUPLICATE_ROW) == 1


def test_max_chars_flag_is_honoured(clean_tree: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--root", str(clean_tree), "--max-chars", "10000"]) == EXIT_OK
    capsys.readouterr()
    assert main(["--root", str(clean_tree), "--max-chars", "5"]) == EXIT_FINDINGS
    out = capsys.readouterr().out
    assert "TOO_LARGE 10_context/pricing.md" in out
    assert "limit 5" in out


CP1252_INDEX = "# \xcdndice\n".encode("cp1252")


def test_main_missing_context_dir_is_usage_error(
    clean_tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (clean_tree / CONTEXT_DIR / "pricing.md").unlink()
    (clean_tree / CONTEXT_DIR).rmdir()
    assert main(["--root", str(clean_tree)]) == EXIT_USAGE
    err = capsys.readouterr().err
    assert CONTEXT_DIR in err
    assert "not found" in err


def test_main_missing_sources_dir_is_usage_error(
    clean_tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (clean_tree / SOURCES_DIR / "pricing.pdf").unlink()
    (clean_tree / SOURCES_DIR).rmdir()
    assert main(["--root", str(clean_tree)]) == EXIT_USAGE
    assert SOURCES_DIR in capsys.readouterr().err


def test_two_index_rows_sharing_an_id_are_only_a_duplicate_drive_id(clean_tree: Path) -> None:
    _write_index(
        clean_tree,
        [
            IndexRow("10_context/pricing.md", "abc", "Pricing extract", "always", "me"),
            IndexRow("20_sources/pricing.pdf", "abc", "Pricing original", "detail", "me"),
        ],
    )
    findings = check(clean_tree)
    assert findings == [
        Finding(
            FindingKind.DUPLICATE_DRIVE_ID,
            "10_context/pricing.md",
            "Drive ID abc also used by 20_sources/pricing.pdf",
        )
    ]


def test_a_canonical_id_reused_by_a_row_is_only_a_duplicate_project_id(clean_tree: Path) -> None:
    _write_index(
        clean_tree,
        [
            IndexRow("10_context/pricing.md", "index-file-id", "Pricing extract", "always", "me"),
            IndexRow("20_sources/pricing.pdf", "abc", "Pricing original", "detail", "me"),
        ],
    )
    findings = check(clean_tree)
    assert [f.kind for f in findings] == [FindingKind.DUPLICATE_PROJECT_ID]
    assert findings[0].path == INSTRUCTIONS_FILE
    assert "index-file-id" in findings[0].detail
    assert "10_context/pricing.md" in findings[0].detail


def test_unreadable_instructions_is_reported(clean_tree: Path) -> None:
    (clean_tree / INSTRUCTIONS_FILE).write_bytes("Drive IDs caf\xe9\n".encode("latin-1"))
    findings = check(clean_tree)
    assert [f.kind for f in findings] == [FindingKind.UNREADABLE]
    assert findings[0].path == INSTRUCTIONS_FILE
    assert findings[0].detail.startswith("UnicodeDecodeError: ")


def test_missing_drive_ids_section_is_reported(clean_tree: Path) -> None:
    (clean_tree / INSTRUCTIONS_FILE).write_text("# Project\n\nNo identities here.\n", "utf-8")
    findings = check(clean_tree)
    assert findings == [
        Finding(
            FindingKind.MISSING_PROJECT_ID,
            INSTRUCTIONS_FILE,
            "Drive IDs section is missing",
        )
    ]


def test_main_missing_instructions_is_usage_error(
    clean_tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (clean_tree / INSTRUCTIONS_FILE).unlink()
    assert main(["--root", str(clean_tree)]) == EXIT_USAGE
    err = capsys.readouterr().err
    assert INSTRUCTIONS_FILE in err
    assert "not found" in err


def test_main_missing_log_is_usage_error(
    clean_tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (clean_tree / LOG_FILE).unlink()
    assert main(["--root", str(clean_tree)]) == EXIT_USAGE
    err = capsys.readouterr().err
    assert LOG_FILE in err
    assert "not found" in err


def test_main_non_utf8_index_is_usage_error(
    clean_tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (clean_tree / INDEX_FILE).write_bytes(CP1252_INDEX)
    assert main(["--root", str(clean_tree)]) == EXIT_USAGE
    assert "is not readable as UTF-8 text" in capsys.readouterr().err
