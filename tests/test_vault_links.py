"""Vault wikilinks resolve against every project file, the way Obsidian resolves them."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from check_index import Finding, FindingKind, check
from common import (
    CONTEXT_DIR,
    INDEX_FILE,
    INSTRUCTIONS_FILE,
    LOG_FILE,
    SOURCES_DIR,
    TEMPLATES_DIR,
    IndexRow,
    fill_template,
    render_index_table,
    wikilinks,
)

FRONTMATTER = (
    '---\ntitle: "Nota"\nsource: "20_sources/informe.pdf"\ndrive_id: "nota-id"\n'
    'updated: "2026-09-27"\nowner: "Ana"\n---\n'
)


@pytest.fixture()
def vault(tmp_path: Path) -> Path:
    (tmp_path / CONTEXT_DIR).mkdir()
    (tmp_path / SOURCES_DIR).mkdir()
    (tmp_path / INSTRUCTIONS_FILE).write_text(
        "# P\n\nVault: yes.\n\n## Drive IDs\n\n"
        "- Project folder: p-id\n- 10_context folder: c-id\n- 20_sources folder: s-id\n"
        "- 01_INDEX: i-id\n- 90_LOG: l-id\n",
        encoding="utf-8",
    )
    (tmp_path / LOG_FILE).write_text("# Log\n", encoding="utf-8")
    (tmp_path / SOURCES_DIR / "informe.pdf").write_bytes(b"%PDF")
    (tmp_path / SOURCES_DIR / "figura.png").write_bytes(b"\x89PNG")
    (tmp_path / CONTEXT_DIR / "nota.md").write_text(FRONTMATTER + "# Nota\n", encoding="utf-8")
    (tmp_path / INDEX_FILE).write_text(
        "# Index\n\n"
        + render_index_table(
            [
                IndexRow("10_context/nota.md", "nota-id", "Nota", "always", "Ana"),
                IndexRow("20_sources/figura.png", "fig-id", "Figure", "detail", "Ana"),
                IndexRow("20_sources/informe.pdf", "pdf-id", "Report", "detail", "Ana"),
            ]
        ),
        encoding="utf-8",
    )
    return tmp_path


def _links(root: Path, body: str) -> list[Finding]:
    (root / CONTEXT_DIR / "nota.md").write_text(FRONTMATTER + "# Nota\n\n" + body, "utf-8")
    return [f for f in check(root) if f.kind is FindingKind.BROKEN_LINK]


@pytest.mark.parametrize(
    "body",
    [
        "See [[informe.pdf]].\n",
        "![[figura.png]]\n",
        "Back to [[Nota]] and [[NOTA.md]].\n",
        "[[20_sources/informe.pdf]] and [[10_context/nota]].\n",
        "[[01_INDEX]] and [[90_log.md]].\n",
        "| Link | Why |\n| --- | --- |\n| [[nota\\|this note]] | alias in a table |\n",
    ],
)
def test_links_to_any_project_file_resolve(vault: Path, body: str) -> None:
    assert _links(vault, body) == []


def test_a_non_markdown_file_needs_its_extension(vault: Path) -> None:
    assert _links(vault, "[[informe]]\n") == [
        Finding(FindingKind.BROKEN_LINK, "10_context/nota.md", "wikilink target not found: informe")
    ]


def test_links_inside_code_are_not_links(vault: Path) -> None:
    body = "Write `[[wikilinks]]` like this:\n\n```\n[[example]]\n```\n"
    assert _links(vault, body) == []


def test_a_file_outside_the_project_is_still_a_broken_link(vault: Path) -> None:
    findings = _links(vault, "[[Private note]] and ![[Pasted image.png]]\n")
    assert [f.detail.split(";")[0] for f in findings] == [
        "wikilink target not found: Private note",
        "embed target not found: Pasted image.png",
    ]
    assert "20_sources with an index row" in findings[1].detail


def test_wikilinks_reports_embeds_and_drops_aliases_and_headings() -> None:
    text = "[[a|b]] ![[c.png]] [[d#part]] [[e\\|f]] `[[g]]`"
    assert wikilinks(text) == [("a", False), ("c.png", True), ("d", False), ("e", False)]


def test_the_vault_extract_template_passes_once_filled(vault: Path) -> None:
    template = (TEMPLATES_DIR / "source-extract-vault.md").read_text(encoding="utf-8")
    extract = fill_template(
        template,
        {
            "TITLE": "Nota",
            "SOURCE_FILE": "informe.pdf",
            "EXTRACT_ID": "nota-id",
            "SOURCE_ID": "pdf-id",
            "DATE": dt.date(2026, 9, 27).isoformat(),
            "AUTHOR": "Ana",
        },
    )
    (vault / CONTEXT_DIR / "nota.md").write_text(extract, encoding="utf-8")
    assert check(vault) == []
