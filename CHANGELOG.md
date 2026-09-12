# Changelog

All notable changes to this project are documented here. The format follows Keep a Changelog and the project uses semantic versioning.

## [Unreleased]

## [0.2.0] - 2026-09-12

### Added

- GitHub Actions CI across Python 3.10-3.13 with pytest, Ruff and mypy gates.
- Obsidian/vault mode with required frontmatter, wikilink validation and `references/vault-setup.md`.
- `check_sync.py` to compare a local project with a Drive listing CSV.
- Index integrity findings for missing/duplicate Drive IDs, missing/colliding canonical project IDs and invalid source references.
- Stable rename recovery in `build_index.py` using unique `drive_id` frontmatter.
- Durable architecture documentation under `docs/architecture/`.
- Compatibility matrix separating protocol compatibility from verified connector behavior.

### Changed

- Repositioned the project as a portable project-memory/governance layer; Claude remains the reference implementation.
- `build_index.py --write` now refuses destructive stale-row removal unless `--allow-drop` is explicit.
- Successful index writes refresh the `Last updated` date.
- Group governance now respects Drive Commenter permissions: members propose; owners record and merge.
- Setup fills role/tone defaults and supports `--vault` for md projects.
- `00_INSTRUCTIONS` no longer stores its own Drive ID, removing the circular setup paste step.
- Source validation now checks the referenced path and Drive ID rather than merely testing for the presence of a `Source:` line.

## [0.1.0] - 2026-09-11

### Added

- SKILL.md with five workflows: setup, session start, ingest, decision logging, maintenance.
- Templates for 00_INSTRUCTIONS, 01_INDEX, 90_LOG, source extracts, the project instruction block and a vendor-neutral instruction block for other assistants, plus mode fragments for solo, duo and group.
- References: verified Google Drive connector behavior and the mode governance table.
- Scripts: init_project, build_index, check_index (standard library, exit-code verdicts) with a pytest suite.
- check_index reports six kinds of finding: MISSING_ROW, STALE_ROW, TOO_LARGE, DUPLICATE_TOPIC, UNREADABLE and DUPLICATE_ROW.
- Example project under examples/sample-project.
- Installers for Claude Code (install.ps1, install.sh).

[Unreleased]: https://github.com/EERamos/drive-shared-projects/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/EERamos/drive-shared-projects/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/EERamos/drive-shared-projects/releases/tag/v0.1.0
