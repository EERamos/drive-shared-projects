"""Templates ship the sections and placeholders the workflows rely on."""

from __future__ import annotations

from pathlib import Path

import pytest

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"


def _read(name: str) -> str:
    return (TEMPLATES / name).read_text(encoding="utf-8")


def test_instructions_template_has_role_sections() -> None:
    text = _read("00_INSTRUCTIONS.md")
    assert "## Assistants and roles" in text
    assert "## Change orders" in text
    for key in ("{{DRAFTER}}", "{{WRITER}}", "{{VERIFIER}}"):
        assert key in text


def test_change_order_template_has_five_fields() -> None:
    text = _read("change-order.md")
    for heading in (
        "## 1. Target",
        "## 2. What changes and why",
        "## 3. Exact text",
        "## 4. What must be true after the write",
        "## 5. Who applies it and record",
    ):
        assert heading in text


def test_ingest_order_template_has_six_sections_and_staging() -> None:
    text = _read("ingest-order.md")
    for heading in (
        "## 1. Sources to copy",
        "## 2. Exclusions",
        "## 3. Extracts to create",
        "## 4. Index rows to add",
        "## 5. Log entry to add",
        "## 6. Execution and verification",
    ):
        assert heading in text
    assert "_staging" in text


@pytest.mark.parametrize("role", ["drafter", "writer", "verifier"])
def test_role_blocks_carry_the_ids_and_the_folder(role: str) -> None:
    text = _read(f"roles/{role}.md")
    for key in ("{{INSTRUCTIONS_ID}}", "{{INDEX_ID}}", "{{LOG_ID}}", "{{FOLDER_PATH}}"):
        assert key in text
    assert "00_INSTRUCTIONS" in text
    assert "01_INDEX" in text


def test_writer_block_never_recreates_and_uses_staging() -> None:
    text = _read("roles/writer.md")
    assert "never replace a document by creating a new one" in text
    assert "_staging" in text


def test_verifier_block_is_read_only() -> None:
    assert "Do not write to 10_context, 01_INDEX or 90_LOG" in _read("roles/verifier.md")


def test_claude_block_mentions_change_orders() -> None:
    text = _read("project-instruction.md")
    assert "change order" in text
    assert "never modify a document that already exists" in text
