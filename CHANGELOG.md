# Changelog

All notable changes to this project are documented here. The format follows Keep a Changelog and the project uses semantic versioning.

## [Unreleased]

## [0.3.0] - 2026-09-17

### Added

- Assistant roles (drafter, writer, verifier) recorded in `00_INSTRUCTIONS`, with `init_project.py --drafter/--writer/--verifier`; defaults reproduce v0.2.0.
- The change order as the only path for a change to an existing document: `templates/change-order.md`, Workflow 7.
- The ingest order for bulk ingests, with a transient `_staging/` folder, batch verification and commit by moving: `templates/ingest-order.md`, Workflow 8.
- Per-role instruction blocks in `templates/roles/`.
- `references/assistant-roles.md` with the writer verification test and the status table per assistant.
- `tests/test_templates.py` and `tests/test_docs.py`.

### Changed

- `Connector constraint` in SKILL.md becomes `Write paths`; four new global rules (change orders, ingest orders, read-back after every write, decide the split before writing).
- Setup collects roles; ingest and decision workflows route writes through change orders.
- Connector reference: Markdown-to-Doc conversion joins single-newline lines into one paragraph; two checklist rows recorded as passed on 2026-09-17.
- README compatibility table gains a "Writes in place" column; ChatGPT recorded as a verified writer.
- The Claude and generic instruction blocks become drafter blocks.
- Sample project carries the new sections.
- `create_project()` takes its options after `today` as keyword-only arguments.
- Ingest orders: when a project has no writer assistant, the drafter creates the staged files and the owner checks them against the manifest before the commit.

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

[Unreleased]: https://github.com/EERamos/drive-shared-projects/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/EERamos/drive-shared-projects/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/EERamos/drive-shared-projects/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/EERamos/drive-shared-projects/releases/tag/v0.1.0
