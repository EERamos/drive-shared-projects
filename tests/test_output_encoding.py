"""Every script prints UTF-8, whatever encoding Python would pick for its output.

On Windows, output that another program reads, as Claude Code does, is encoded in the ANSI
code page. The subprocess tests set PYTHONIOENCODING=cp1252 to get that on every platform.
"""

from __future__ import annotations

import datetime as dt
import io
import os
import subprocess
import sys
from pathlib import Path

import pytest

from common import CONTEXT_DIR, INDEX_FILE, Format, Mode, use_utf8_output
from init_project import create_project

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
NAME = "Plan → envíos.md"  # the arrow is outside cp1252, the accent is not
PATH = f"{CONTEXT_DIR}/{NAME}"


def _run(script: str, *args: str | Path) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *map(str, args)],
        capture_output=True,
        env={**os.environ, "PYTHONIOENCODING": "cp1252"},
        check=False,
    )


def _output(result: subprocess.CompletedProcess[bytes]) -> str:
    assert b"Traceback" not in result.stderr, result.stderr.decode("utf-8", "replace")
    return result.stdout.decode("utf-8")


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    create_project(root, "P", Mode.SOLO, Format.MD, "Ana", dt.date(2026, 9, 28))
    (root / PATH).write_text("# Plan\n", encoding="utf-8")
    return root


def test_check_index_lists_a_name_outside_the_code_page(project: Path) -> None:
    result = _run("check_index.py", "--root", project)
    assert f"MISSING_ROW {PATH}" in _output(result)
    assert result.returncode == 1


def test_build_index_prints_a_row_outside_the_code_page(project: Path) -> None:
    result = _run("build_index.py", "--root", project)
    assert f"| {PATH} | TODO-ID |" in _output(result)
    assert result.returncode == 0


def test_check_sync_lists_a_name_outside_the_code_page(project: Path, tmp_path: Path) -> None:
    csv_path = tmp_path / "drive.csv"
    csv_path.write_text(f"path,drive_id\n{PATH},1plan\n", encoding="utf-8")
    result = _run("check_sync.py", "--root", project, "--drive-csv", csv_path)
    assert f"ID_MISSING {PATH}" in _output(result)
    assert result.returncode == 1


def test_check_drive_lists_a_name_outside_the_code_page(project: Path, tmp_path: Path) -> None:
    instructions = tmp_path / "instructions.md"
    instructions.write_text(
        "# P\n\n## Drive IDs\n\n- Project folder: 1p\n- 10_context folder: 1c\n"
        "- 20_sources folder: 1s\n- 01_INDEX: 1i\n- 90_LOG: 1l\n",
        encoding="utf-8",
    )
    context = tmp_path / "context.csv"
    context.write_text(f"path,drive_id\n{PATH},1plan\n", encoding="utf-8")
    sources = tmp_path / "sources.csv"
    sources.write_text("path,drive_id\n", encoding="utf-8")
    result = _run(
        "check_drive.py",
        "--instructions",
        instructions,
        "--index",
        project / INDEX_FILE,
        "--context-listing",
        context,
        "--sources-listing",
        sources,
    )
    assert f"MISSING_ROW {PATH}" in _output(result)
    assert result.returncode == 1


def test_init_project_prints_a_folder_outside_the_code_page(tmp_path: Path) -> None:
    out = tmp_path / "Envíos → 2026"
    args = ("--name", "P", "--mode", "solo", "--format", "md", "--out", out)
    result = _run("init_project.py", *args)
    assert _output(result) == f"created {out}{os.linesep}"
    assert result.returncode == 0


def test_use_utf8_output_switches_code_page_streams(monkeypatch: pytest.MonkeyPatch) -> None:
    out, err = io.BytesIO(), io.BytesIO()
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(out, encoding="cp1252", newline="\n"))
    monkeypatch.setattr(sys, "stderr", io.TextIOWrapper(err, encoding="cp1252", newline="\n"))
    use_utf8_output()
    print(NAME)
    print("\udcff", file=sys.stderr)  # an undecodable byte in a POSIX file name
    sys.stdout.flush()
    sys.stderr.flush()
    assert out.getvalue() == f"{NAME}\n".encode()
    assert err.getvalue() == b"\\udcff\n"


def test_use_utf8_output_leaves_other_streams_alone(monkeypatch: pytest.MonkeyPatch) -> None:
    buffer = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buffer)
    monkeypatch.setattr(sys, "stderr", None)  # pythonw.exe has no console streams
    use_utf8_output()
    assert sys.stdout is buffer
