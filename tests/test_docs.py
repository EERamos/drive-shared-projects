"""SKILL.md, references and README carry the sections the workflows and scripts rely on."""

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


def test_readme_changelog_and_version_are_0_4_0() -> None:
    readme = _read("README.md")
    assert "Writes in place" in readme
    assert "7. **Change order**" in readme
    assert "8. **Ingest order**" in readme
    assert "## Assistant roles, change orders and ingest orders" in readme
    assert "## [0.4.0]" in _read("CHANGELOG.md")
    assert 'version = "0.4.0"' in _read("pyproject.toml")


def test_no_document_asks_for_a_subfolder_under_20_sources() -> None:
    for rel in ("SKILL.md", "references/assistant-roles.md", "templates/ingest-order.md"):
        text = _read(rel)
        assert "target subfolder" not in text
        assert "Target under 20_sources" not in text
    assert "no subfolders" in _read("templates/00_INSTRUCTIONS.md")


def test_the_size_cap_prose_names_the_byte_count() -> None:
    for rel in (
        "SKILL.md",
        "README.md",
        "references/drive-connector-behavior.md",
        "templates/00_INSTRUCTIONS.md",
    ):
        assert "UTF-8 bytes" in _read(rel) or "UTF-8 byte count" in _read(rel)


def test_vault_setup_covers_renames_settings_and_synchronizers() -> None:
    text = _read("references/vault-setup.md")
    for heading in (
        "## Obsidian settings",
        "## Renames",
        "## Drive IDs of a vault project",
        "## Verified synchronizers",
    ):
        assert heading in text
    assert "rclone sync --track-renames" in text


def test_workflow_6_offers_the_drive_check_and_the_csv() -> None:
    workflow = _read("SKILL.md").split("## Workflow 6")[1].split("## Workflow 7")[0]
    assert "check_drive.py" in workflow
    assert "check_sync.py" in workflow
