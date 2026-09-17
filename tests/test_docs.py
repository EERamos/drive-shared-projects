"""SKILL.md, references and README carry the v0.3.0 sections the spec promises."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_roles_reference_has_test_status_and_ingest_order() -> None:
    text = _read("references/assistant-roles.md")
    assert "## Writer verification test" in text
    assert "## Status by assistant" in text
    assert "## Ingest order" in text
    assert "_staging" in text


def test_connector_reference_records_paragraph_merging() -> None:
    assert "single newline" in _read("references/drive-connector-behavior.md")


def test_modes_reference_mentions_assistant_roles() -> None:
    assert "Assistant roles are independent of the mode" in _read("references/modes.md")


def test_skill_has_write_paths_and_new_workflows() -> None:
    text = _read("SKILL.md")
    assert "## Write paths" in text
    assert "## Connector constraint" not in text
    assert "## Workflow 7: Change order" in text
    assert "## Workflow 8: Ingest order" in text
    assert "_staging" in text
    assert "templates/roles/" in text


def test_readme_changelog_and_version_are_0_3_0() -> None:
    readme = _read("README.md")
    assert "Writes in place" in readme
    assert "7. **Change order**" in readme
    assert "8. **Ingest order**" in readme
    assert "## Assistant roles, change orders and ingest orders" in readme
    assert "## [0.3.0]" in _read("CHANGELOG.md")
    assert 'version = "0.3.0"' in _read("pyproject.toml")
