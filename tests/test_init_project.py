"""Tests for scripts/init_project.py."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from common import CONTEXT_DIR, INDEX_FILE, INSTRUCTIONS_FILE, LOG_FILE, SOURCES_DIR, Format, Mode
from init_project import EXIT_OK, EXIT_REFUSED, EXIT_USAGE, create_project, main

TODAY = dt.date(2026, 9, 11)


def test_create_project_builds_tree_and_fills_placeholders(tmp_path: Path) -> None:
    out = tmp_path / "proj"
    create_project(out, "Demo", Mode.DUO, Format.DOCS, "Edgar", TODAY)

    assert (out / CONTEXT_DIR / ".gitkeep").exists()
    assert (out / SOURCES_DIR / ".gitkeep").exists()
    instructions = (out / INSTRUCTIONS_FILE).read_text(encoding="utf-8")
    assert "# Demo - Project Instructions" in instructions
    assert "Mode: duo. Format: docs. Index owner: Edgar. Created: 2026-09-11." in instructions
    assert "Edgar owns the index" in instructions
    assert "{{" not in instructions
    index = (out / INDEX_FILE).read_text(encoding="utf-8")
    assert "| File | Drive ID | What it contains | When to read | Owner |" in index
    log = (out / LOG_FILE).read_text(encoding="utf-8")
    assert "### 2026-09-11 - Project created" in log
    assert "- Author: Edgar" in log


def test_create_project_refuses_non_empty_dir(tmp_path: Path) -> None:
    out = tmp_path / "proj"
    out.mkdir()
    (out / "something.txt").write_text("x", encoding="utf-8")
    with pytest.raises(FileExistsError):
        create_project(out, "Demo", Mode.SOLO, Format.MD, "me", TODAY)


def test_create_project_accepts_empty_existing_dir(tmp_path: Path) -> None:
    out = tmp_path / "proj"
    out.mkdir()
    create_project(out, "Demo", Mode.SOLO, Format.MD, "me", TODAY)
    assert (out / INSTRUCTIONS_FILE).exists()


@pytest.mark.parametrize("mode", list(Mode))
def test_each_mode_injects_its_fragment(tmp_path: Path, mode: Mode) -> None:
    out = tmp_path / mode.value
    create_project(out, "Demo", mode, Format.MD, "Ana", TODAY)
    text = (out / INSTRUCTIONS_FILE).read_text(encoding="utf-8")
    assert f"## Mode rules ({mode.value})" in text
    assert "{{MODE_RULES}}" not in text
    assert "{{OWNER}}" not in text


def test_main_happy_path(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "p"
    code = main(["--name", "Demo", "--mode", "solo", "--format", "md", "--out", str(out)])
    assert code == EXIT_OK
    assert (out / INDEX_FILE).exists()
    assert "created" in capsys.readouterr().out


def test_main_refused(tmp_path: Path) -> None:
    out = tmp_path / "p"
    out.mkdir()
    (out / "x").write_text("x", encoding="utf-8")
    code = main(["--name", "Demo", "--mode", "solo", "--format", "md", "--out", str(out)])
    assert code == EXIT_REFUSED


def test_main_bad_mode_is_usage_error(tmp_path: Path) -> None:
    code = main(
        ["--name", "Demo", "--mode", "trio", "--format", "md", "--out", str(tmp_path / "p")]
    )
    assert code == EXIT_USAGE
