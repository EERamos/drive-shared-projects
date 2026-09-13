# Changelog

All notable changes to this project are documented here. The format follows Keep a Changelog and the project uses semantic versioning.

## [Unreleased]

### Added

- `check_drive.py`: validates `01_INDEX` against Drive listings saved from the connector (`read_file_content` and `search_files` results; Markdown and `path,drive_id` CSV accepted too). One listing per folder: `--context-listing` and `--sources-listing` are mandatory and bound to their folder, `--project-listing` is optional. Reports missing/stale rows, renames by stable ID, ID mismatches, duplicate titles, nested folders and, with a project listing, the fixed layout, both variants of a canonical file and the canonical IDs.
- `parse_drive_csv_rows` keeps duplicate CSV paths, so `DUPLICATE_TITLE` also applies to CSV listings; `check_sync` keeps the last ID per path as before.
- `common.connector_markdown` and `normalize_connector_markdown`: turn Markdown as the connector returns it (escaped punctuation, indented bullets, bold index header above an empty row, `<!-- end list -->`) into what the parsers expect.
- Connector samples captured on 2026-09-13 under `tests/fixtures/connector/`, anonymised, with the behaviour recorded in `references/drive-connector-behavior.md`.
- SKILL.md: Docs-format maintenance procedure for Claude Code and the manual equivalent for claude.ai; what "paste" means for an index row and a log entry in Docs.

### Changed

- `source_reference` tolerates the `Extracted:` tail that Google Docs joins onto the `Source:` line; the extract templates and the example separate the two lines with a blank line.
- `check_index.py` and `check_sync.py` share the canonical-ID, duplicate-row and CSV helpers with the new script; their findings are unchanged.
- Templates document the Docs File cell convention (`10_context/<Drive title>`) and the title-uniqueness rule.

## [0.2.0] - 2026-09-12

### Added

- GitHub Actions CI across Python 3.10-3.13 with pytest, Ruff and mypy gates.
- Obsidian/vault mode with required frontmatter, wikilink validation and `references/vault-setup.md`.
- `check_sync.py` to compare a local project with a Drive listing CSV.
- Index integrity findings for missing/duplicate Drive IDs, missing/colliding canonical project IDs and invalid source references.
- Stable rename recovery in `build_index.py` using unique `drive_id` frontmatter.
- Durable architecture documentation under `docs/architecture/`.
- Compatibility matrix separating protocol compatibility from verified connector behavior.
- `ID_MISSING` in `check_sync`: a path present on both sides that records a Drive ID on only one of them.

### Changed

- Repositioned the project as a portable project-memory/governance layer; Claude remains the reference implementation.
- `build_index.py --write` now refuses destructive stale-row removal unless `--allow-drop` is explicit.
- Successful index writes refresh the `Last updated` date.
- Group governance now respects Drive Commenter permissions: members propose; owners record and merge.
- Setup fills role/tone defaults and supports `--vault` for md projects.
- `00_INSTRUCTIONS` no longer stores its own Drive ID, removing the circular setup paste step.
- Source validation now checks the referenced path and Drive ID rather than merely testing for the presence of a `Source:` line.
- All scripts require `00_INSTRUCTIONS.md` and `90_LOG.md`: `build_index`, `check_index` and `check_sync` exit 2 when any of the five project paths is missing.
- A Drive IDs section that is missing or unreadable in `00_INSTRUCTIONS` is now a finding instead of a silently skipped check.
- `DUPLICATE_PROJECT_ID` is reported only when a canonical project ID is involved; a collision between two index rows stays `DUPLICATE_DRIVE_ID`.
- CI actions updated to `actions/checkout@v7` and `actions/setup-python@v7`.

### Removed

- `DUPLICATE_TOPIC` and the filename-based topic heuristic; explicit `Source:` references are the only extract-to-source relationship.

## [0.1.0] - 2026-09-11

### Added

- SKILL.md with five workflows: setup, session start, ingest, decision logging, maintenance.
- Templates for 00_INSTRUCTIONS, 01_INDEX, 90_LOG, source extracts, the project instruction block and a vendor-neutral instruction block for other assistants, plus mode fragments for solo, duo and group.
- References: verified Google Drive connector behavior and the mode governance table.
- Scripts: init_project, build_index, check_index (standard library, exit-code verdicts) with a pytest suite.
- check_index reports six kinds of finding: MISSING_ROW, STALE_ROW, TOO_LARGE, DUPLICATE_TOPIC, UNREADABLE (a file in 10_context that is not UTF-8 text) and DUPLICATE_ROW (the same file listed by more than one row).
- build_index --write reports on stderr how many stale rows it removed and warns about duplicate rows, so no deletion is silent.
- build_index and check_index exit 2 when 01_INDEX.md, 10_context or 20_sources is missing, or when the index is not UTF-8 text.
- Example project under examples/sample-project.
- Installers for Claude Code (install.ps1, install.sh).

[Unreleased]: https://github.com/EERamos/drive-shared-projects/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/EERamos/drive-shared-projects/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/EERamos/drive-shared-projects/releases/tag/v0.1.0
