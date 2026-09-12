from __future__ import annotations

from pathlib import Path

import pytest

from check_sync import SyncFindingKind, check_sync, main, read_drive_csv
from common import (
    CONTEXT_DIR,
    INDEX_FILE,
    INSTRUCTIONS_FILE,
    LOG_FILE,
    SOURCES_DIR,
    IndexRow,
    render_index_table,
)


def _project(tmp_path: Path) -> Path:
    (tmp_path / CONTEXT_DIR).mkdir()
    (tmp_path / SOURCES_DIR).mkdir()
    (tmp_path / CONTEXT_DIR / "a.md").write_text("# A\n", encoding="utf-8")
    (tmp_path / INSTRUCTIONS_FILE).write_text(
        "# P\n\n## Drive IDs\n\n- 01_INDEX: index-id\n- 90_LOG: log-id\n",
        encoding="utf-8",
    )
    (tmp_path / LOG_FILE).write_text("# Log\n", encoding="utf-8")
    (tmp_path / INDEX_FILE).write_text(
        "# Index\n\n"
        + render_index_table([IndexRow("10_context/a.md", "a-id", "A", "always", "Ana")]),
        encoding="utf-8",
    )
    return tmp_path


def test_read_drive_csv_requires_columns(tmp_path: Path) -> None:
    csv_path = tmp_path / "drive.csv"
    csv_path.write_text("path,drive_id\n10_context/a.md,a-id\n", encoding="utf-8")
    assert read_drive_csv(csv_path) == {"10_context/a.md": "a-id"}


def test_sync_clean_and_mismatch(tmp_path: Path) -> None:
    root = _project(tmp_path)
    remote = {
        "00_INSTRUCTIONS.md": "instructions-id",
        "01_INDEX.md": "index-id",
        "10_context/a.md": "a-id",
        "90_LOG.md": "log-id",
    }
    assert check_sync(root, remote) == []
    remote["10_context/a.md"] = "different"
    findings = check_sync(root, remote)
    assert [f.kind for f in findings] == [SyncFindingKind.ID_MISMATCH]


def test_sync_reports_a_drive_id_missing_on_the_drive_side(tmp_path: Path) -> None:
    root = _project(tmp_path)
    remote = {
        "00_INSTRUCTIONS.md": "instructions-id",
        "01_INDEX.md": "index-id",
        "10_context/a.md": "",
        "90_LOG.md": "log-id",
    }
    findings = check_sync(root, remote)
    assert [f.kind for f in findings] == [SyncFindingKind.ID_MISSING]
    assert findings[0].path == "10_context/a.md"
    assert findings[0].detail == "Drive ID missing (local has a-id)"


def test_sync_reports_a_drive_id_missing_on_the_local_side(tmp_path: Path) -> None:
    root = _project(tmp_path)
    (root / INDEX_FILE).write_text(
        "# Index\n\n"
        + render_index_table([IndexRow("10_context/a.md", "TODO-ID", "A", "always", "Ana")]),
        encoding="utf-8",
    )
    remote = {
        "00_INSTRUCTIONS.md": "instructions-id",
        "01_INDEX.md": "index-id",
        "10_context/a.md": "a-id",
        "90_LOG.md": "log-id",
    }
    findings = check_sync(root, remote)
    assert [f.kind for f in findings] == [SyncFindingKind.ID_MISSING]
    assert findings[0].path == "10_context/a.md"
    assert findings[0].detail == "local ID missing (Drive has a-id)"


def test_sync_accepts_the_missing_self_id_of_the_instructions_file(tmp_path: Path) -> None:
    root = _project(tmp_path)
    remote = {
        "00_INSTRUCTIONS.md": "instructions-id",
        "01_INDEX.md": "index-id",
        "10_context/a.md": "a-id",
        "90_LOG.md": "log-id",
    }
    assert check_sync(root, remote) == []


def test_sync_reports_local_and_drive_only(tmp_path: Path) -> None:
    root = _project(tmp_path)
    findings = check_sync(root, {"remote-only.md": "x"})
    kinds = [f.kind for f in findings]
    assert SyncFindingKind.LOCAL_ONLY in kinds
    assert SyncFindingKind.DRIVE_ONLY in kinds


def _drive_csv(tmp_path: Path) -> Path:
    csv_path = tmp_path / "drive.csv"
    csv_path.write_text(
        "path,drive_id\n"
        "00_INSTRUCTIONS.md,instructions-id\n"
        "01_INDEX.md,index-id\n"
        "10_context/a.md,a-id\n"
        "90_LOG.md,log-id\n",
        encoding="utf-8",
    )
    return csv_path


def test_main(tmp_path: Path) -> None:
    root = _project(tmp_path)
    csv_path = _drive_csv(tmp_path)
    assert main(["--root", str(root), "--drive-csv", str(csv_path)]) == 0


def test_main_missing_instructions_is_usage_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _project(tmp_path)
    csv_path = _drive_csv(tmp_path)
    (root / INSTRUCTIONS_FILE).unlink()
    assert main(["--root", str(root), "--drive-csv", str(csv_path)]) == 2
    err = capsys.readouterr().err
    assert INSTRUCTIONS_FILE in err
    assert "not found" in err


def test_main_missing_log_is_usage_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _project(tmp_path)
    csv_path = _drive_csv(tmp_path)
    (root / LOG_FILE).unlink()
    assert main(["--root", str(root), "--drive-csv", str(csv_path)]) == 2
    err = capsys.readouterr().err
    assert LOG_FILE in err
    assert "not found" in err
