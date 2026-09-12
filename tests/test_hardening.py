from __future__ import annotations

import datetime as dt
from pathlib import Path

from build_index import EXIT_REFUSED, dropped_rows, merge, scan
from build_index import main as build_main
from check_index import FindingKind, check
from common import (
    CONTEXT_DIR,
    INDEX_FILE,
    INSTRUCTIONS_FILE,
    SOURCES_DIR,
    Format,
    IndexRow,
    Mode,
    parse_frontmatter,
    render_index_table,
    source_reference,
    wikilink_targets,
)
from init_project import EXIT_USAGE, create_project
from init_project import main as init_main


def _base_tree(tmp_path: Path, *, vault: bool = False) -> Path:
    (tmp_path / CONTEXT_DIR).mkdir()
    (tmp_path / SOURCES_DIR).mkdir()
    (tmp_path / INSTRUCTIONS_FILE).write_text(
        "# Project\n\nMode: solo. Format: md. Index owner: Ana. Created: 2026-09-12.\n"
        + ("Vault: yes.\n" if vault else "Vault: no.\n"),
        encoding="utf-8",
    )
    return tmp_path


def _write_index(root: Path, rows: list[IndexRow], date: str = "2026-09-01") -> None:
    (root / INDEX_FILE).write_text(
        f"# Index\n\nIndex owner: Ana. Last updated: {date}.\n\n## Files\n\n"
        + render_index_table(rows),
        encoding="utf-8",
    )


def test_frontmatter_and_wikilinks_helpers() -> None:
    text = '---\ntitle: "A"\ndrive_id: id1\n---\n# A\n[[B|label]] [[sub/C#part]]'
    assert parse_frontmatter(text) == {"title": "A", "drive_id": "id1"}
    assert wikilink_targets(text) == ["B", "sub/C"]


def test_source_reference_parses_path_and_id() -> None:
    assert source_reference("Source: 20_sources/a.pdf (Drive ID: abc)\n") == (
        "20_sources/a.pdf",
        "abc",
    )


def test_merge_recognizes_rename_by_stable_drive_id() -> None:
    existing = [IndexRow("10_context/old.md", "id-1", "Human", "always", "Ana")]
    scanned = [IndexRow("10_context/new.md", "id-1", "Fresh", "", "")]
    assert merge(existing, scanned) == [
        IndexRow("10_context/new.md", "id-1", "Human", "always", "Ana")
    ]
    assert dropped_rows(existing, scanned) == []


def test_build_write_refuses_drop_and_refreshes_date(tmp_path: Path) -> None:
    root = _base_tree(tmp_path)
    (root / CONTEXT_DIR / "kept.md").write_text("# Kept\n", encoding="utf-8")
    _write_index(
        root,
        [
            IndexRow("10_context/kept.md", "id1", "Kept", "always", "Ana"),
            IndexRow("10_context/gone.md", "id2", "Gone", "never", "Ana"),
        ],
    )
    before = (root / INDEX_FILE).read_text(encoding="utf-8")
    assert build_main(["--root", str(root), "--write"]) == EXIT_REFUSED
    assert (root / INDEX_FILE).read_text(encoding="utf-8") == before
    assert build_main(["--root", str(root), "--write", "--allow-drop"]) == 0
    after = (root / INDEX_FILE).read_text(encoding="utf-8")
    assert f"Last updated: {dt.date.today().isoformat()}" in after
    assert "10_context/gone.md" not in after


def test_scan_reads_title_drive_id_and_owner_from_frontmatter(tmp_path: Path) -> None:
    root = _base_tree(tmp_path, vault=True)
    (root / CONTEXT_DIR / "renamed.md").write_text(
        '---\ntitle: "Stable title"\nsource: "20_sources/x.pdf"\n'
        'drive_id: "id-9"\nupdated: "2026-09-12"\nowner: "Ana"\n---\n# Other\n',
        encoding="utf-8",
    )
    assert scan(root) == [IndexRow("10_context/renamed.md", "id-9", "Stable title", "", "Ana")]


def test_check_reports_missing_and_duplicate_drive_ids(tmp_path: Path) -> None:
    root = _base_tree(tmp_path)
    (root / CONTEXT_DIR / "a.md").write_text("# A\n", encoding="utf-8")
    (root / SOURCES_DIR / "b.pdf").write_bytes(b"pdf")
    _write_index(
        root,
        [
            IndexRow("10_context/a.md", "TODO-ID", "A", "always", "Ana"),
            IndexRow("20_sources/b.pdf", "TODO-ID", "B", "detail", "Ana"),
        ],
    )
    kinds = [f.kind for f in check(root)]
    assert kinds.count(FindingKind.MISSING_DRIVE_ID) == 2

    _write_index(
        root,
        [
            IndexRow("10_context/a.md", "same", "A", "always", "Ana"),
            IndexRow("20_sources/b.pdf", "same", "B", "detail", "Ana"),
        ],
    )
    assert FindingKind.DUPLICATE_DRIVE_ID in {f.kind for f in check(root)}


def test_check_validates_source_path_and_drive_id(tmp_path: Path) -> None:
    root = _base_tree(tmp_path)
    (root / CONTEXT_DIR / "pricing.md").write_text(
        "# Pricing\n\nSource: 20_sources/pricing.pdf (Drive ID: wrong)\n", encoding="utf-8"
    )
    (root / SOURCES_DIR / "pricing.pdf").write_bytes(b"pdf")
    _write_index(
        root,
        [
            IndexRow("10_context/pricing.md", "ctx", "Pricing", "always", "Ana"),
            IndexRow("20_sources/pricing.pdf", "src", "Source", "detail", "Ana"),
        ],
    )
    findings = check(root)
    assert any(f.kind is FindingKind.INVALID_SOURCE_REFERENCE for f in findings)
    assert "wrong" in next(
        f.detail for f in findings if f.kind is FindingKind.INVALID_SOURCE_REFERENCE
    )


def test_vault_requires_frontmatter_and_resolves_wikilinks(tmp_path: Path) -> None:
    root = _base_tree(tmp_path, vault=True)
    (root / SOURCES_DIR / "a.pdf").write_bytes(b"pdf")
    (root / CONTEXT_DIR / "a.md").write_text(
        "# A\n\nSource: 20_sources/a.pdf (Drive ID: src)\n[[Missing]]\n", encoding="utf-8"
    )
    _write_index(
        root,
        [
            IndexRow("10_context/a.md", "ctx", "A", "always", "Ana"),
            IndexRow("20_sources/a.pdf", "src", "Source", "detail", "Ana"),
        ],
    )
    kinds = {f.kind for f in check(root)}
    assert FindingKind.MISSING_FRONTMATTER in kinds
    assert FindingKind.BROKEN_LINK in kinds


def test_valid_vault_extract_passes(tmp_path: Path) -> None:
    root = _base_tree(tmp_path, vault=True)
    (root / SOURCES_DIR / "a.pdf").write_bytes(b"pdf")
    (root / CONTEXT_DIR / "b.md").write_text(
        '---\ntitle: "B"\nsource: "20_sources/a.pdf"\ndrive_id: "b-id"\n'
        'updated: "2026-09-12"\nowner: "Ana"\n---\n# B\n',
        encoding="utf-8",
    )
    (root / CONTEXT_DIR / "a.md").write_text(
        '---\ntitle: "A"\nsource: "20_sources/a.pdf"\ndrive_id: "a-id"\n'
        'updated: "2026-09-12"\nowner: "Ana"\n---\n# A\n\n'
        "Source: 20_sources/a.pdf (Drive ID: src)\n[[b]]\n",
        encoding="utf-8",
    )
    _write_index(
        root,
        [
            IndexRow("10_context/a.md", "a-id", "A", "always", "Ana"),
            IndexRow("10_context/b.md", "b-id", "B", "related", "Ana"),
            IndexRow("20_sources/a.pdf", "src", "Source", "detail", "Ana"),
        ],
    )
    assert check(root) == []


def test_init_vault_requires_md_and_fills_role_tone(tmp_path: Path) -> None:
    assert (
        init_main(
            [
                "--name",
                "Demo",
                "--mode",
                "solo",
                "--format",
                "docs",
                "--vault",
                "--out",
                str(tmp_path / "bad"),
            ]
        )
        == EXIT_USAGE
    )
    out = tmp_path / "good"
    create_project(
        out,
        "Demo",
        Mode.SOLO,
        Format.MD,
        "Ana",
        dt.date(2026, 9, 12),
        role="quant research assistant",
        tone="technical Spanish",
        vault=True,
        templates=Path(__file__).resolve().parent.parent / "templates",
    )
    instructions = (out / INSTRUCTIONS_FILE).read_text(encoding="utf-8")
    assert "Vault: yes." in instructions
    assert "Assistant role: quant research assistant." in instructions
    assert "Tone and language: technical Spanish." in instructions
    assert "- 00_INSTRUCTIONS:" not in instructions
    assert "{{" not in instructions


def test_check_validates_canonical_project_ids(tmp_path: Path) -> None:
    root = _base_tree(tmp_path)
    (root / CONTEXT_DIR / "a.md").write_text("# A\n", encoding="utf-8")
    _write_index(root, [IndexRow("10_context/a.md", "ctx-id", "A", "always", "Ana")])
    (root / INSTRUCTIONS_FILE).write_text(
        "# Project\n\n## Drive IDs\n\n"
        "- Project folder: TODO-ID\n"
        "- 10_context folder: folder-shared\n"
        "- 20_sources folder: folder-source\n"
        "- 01_INDEX: ctx-id\n"
        "- 90_LOG: log-id\n",
        encoding="utf-8",
    )

    findings = check(root)
    kinds = [finding.kind for finding in findings]
    assert FindingKind.MISSING_PROJECT_ID in kinds
    assert FindingKind.DUPLICATE_PROJECT_ID in kinds
    assert any("Project folder" in finding.detail for finding in findings)
    assert any("ctx-id" in finding.detail for finding in findings)
