"""The shipped example must pass the maintenance check."""

from __future__ import annotations

from pathlib import Path

from check_index import EXIT_OK, check, main

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "sample-project"


def test_example_exists_with_layout() -> None:
    assert (EXAMPLE / "00_INSTRUCTIONS.md").is_file()
    assert (EXAMPLE / "01_INDEX.md").is_file()
    assert (EXAMPLE / "90_LOG.md").is_file()
    assert (EXAMPLE / "10_context").is_dir()
    assert (EXAMPLE / "20_sources").is_dir()


def test_example_passes_check() -> None:
    assert check(EXAMPLE) == []
    assert main(["--root", str(EXAMPLE)]) == EXIT_OK
