# Changelog

All notable changes to this project are documented here. The format follows Keep a Changelog and the project uses semantic versioning.

## [Unreleased]

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

[Unreleased]: https://github.com/EERamos/drive-shared-projects/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/EERamos/drive-shared-projects/releases/tag/v0.1.0
