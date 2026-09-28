# Changelog

All notable changes to this project are documented here. The format follows Keep a Changelog and the project uses semantic versioning.

## [Unreleased]

### Changed

- `templates/01_INDEX.md` no longer writes `<Drive title>` and `<file name>`. Converted to a Google Doc, text between angle brackets is dropped, so the File guidance of every Docs-format index read "10_context/or 20_sources/". A test keeps angle-bracket placeholders out of the templates that become Docs.
- The solo mode fragment says the person may edit files directly while a change an assistant makes still travels as a change order. It read as if no orders were needed, which contradicted the Change orders section of the same instructions once a writer assistant takes part.
- Connector reference, from a test in Claude Code on the web against a real Drive on 2026-09-27. The size cap follows the client, not the connector: Google Docs up to 63,978 bytes read back complete, and above about 50 KB Claude Code saves the result to a file instead of showing it. Folders are created with `contentMimeType`, because the tool marks `mimeType` as deprecated. Read results carry `title` and `viewUrl`, listings carry `fileSize` for Docs too, and angle brackets are dropped on conversion. Three checklist rows record the new environment.
- Workflow 5 and the README: a large result that Claude Code saved to a file is the verbatim JSON, and goes to `check_drive.py` as it is instead of being copied by hand.

## [0.4.0] - 2026-09-27

### Added

- `NESTED_FOLDER` in `check_index.py`: a folder directly inside `10_context` or `20_sources` is a finding, as it already was in `check_drive.py`, so md format stops accepting what Docs format rejects. Dot folders are skipped like dotfiles. Files below the folder are still scanned, so existing rows do not turn stale.
- `ID_MISMATCH` in `check_index.py`: a frontmatter `drive_id` that disagrees with the file's index row is a finding. It applies to every text file `build_index.py` reads identity from, in any md project and in `20_sources` too, because the frontmatter wins there silently. Before, a wrong frontmatter ID passed the check and replaced the row on the next write.
- In vault mode a frontmatter `drive_id` still at `TODO-ID` is reported as `MISSING_DRIVE_ID`, which is what Workflow 3 promised ("treat maintenance as failing until it is populated") and did not happen.
- `build_index.py` names every row whose ID a frontmatter ID replaces, on stderr, in the preview ("would replace") and on write ("replaced"). Which side wins is unchanged. New helper `id_conflicts`.
- Tests that run `check_drive.py` as the Drive check of a flat vault mirror: the local `00_INSTRUCTIONS.md` and `01_INDEX.md` generated from the real templates against saved connector listings with `.md` titles, clean, and after a rename that kept its Drive ID (`RENAMED_FILE`). What the vault documentation promised is now tested.

### Changed

- `check_index.py` applies the context size cap to the UTF-8 byte count, the unit in which the connector limit was observed (30 KB read complete, 54 KB did not). A byte count never falls below the character count, so the cap still bounds characters; accented or non-Latin text now reaches it sooner. The default of 50,000 and the `--max-chars` flag are unchanged, and the `TOO_LARGE` detail reports both counts. SKILL.md, README, the connector reference, the instructions template and the example say so; the connector reference drops its word estimate, which was off by a factor of three.
- `10_context` and `20_sources` are flat in both formats. The ingest order asks for a file name under `20_sources` instead of a target subfolder (SKILL.md Workflow 8, `references/assistant-roles.md`, `templates/ingest-order.md`), which closes the contradiction with `check_drive.py`: an ingest into a subfolder was reported as `NESTED_FOLDER` with its rows `STALE_ROW`. The rule is explicit in SKILL.md, README, the instructions template, the example and the architecture overview.
- `check_drive.py` reports a CSV path below a subfolder as `NESTED_FOLDER` for that subfolder and leaves the file unplaced, as a JSON listing would; before, a nested CSV path passed clean.
- The Drive IDs of `00_INSTRUCTIONS` are read from their section only, up to the next heading of the same level. Before, any `- label: value` line in the file counted and the last one won, so a later line such as a local vault path labelled `Project folder` replaced the canonical ID for `check_index`, `check_drive` and `check_sync`. A heading that starts with `Drive IDs` opens the section; without one the section is missing, as before.
- One rule for dot entries on both sides: `common.is_hidden_path` skips any path with a component that starts with a dot in `scan_files`, in the `check_drive.py` listings (JSON titles and CSV paths, project listing included) and in the `check_sync.py` CSV. A synced `.gitkeep` from `init_project.py` used to come back as `MISSING_ROW` or `DRIVE_ONLY`, and `.obsidian/` in the project listing as `UNEXPECTED_FILE`.
- Vault wikilinks resolve the way Obsidian resolves them: against every file of the project (`10_context`, `20_sources` and the three root files), by path or by file name, ignoring case; a note also resolves without `.md`, any other file needs its extension. `[[informe.pdf]]`, `![[figura.png]]` and `[[Nota]]` for `nota.md` are no longer false `BROKEN_LINK`s, and a link outside the project still is. Links inside inline code and code blocks are ignored, which removes the false positive the vault extract template itself produced; a table alias written `[[nota\|alias]]` now resolves by design rather than by accident. A broken embed says where embedded originals belong: `20_sources`, with an index row. New helper `common.wikilinks` returns each target with its embed flag.
- `parse_frontmatter` accepts a UTF-8 byte order mark before the opening `---`. A BOM added by a Windows editor hid the whole frontmatter and produced `MISSING_FRONTMATTER`.
- `references/vault-setup.md`: the rclone example gains `--track-renames`, with what happens without it (a rename becomes delete plus upload and the `drive_id` is orphaned) and the case the flag cannot cover (rename and edit between two runs). New sections: Obsidian settings (automatic link updates, attachments outside the project, no Excalidraw or Canvas in `10_context`, a template that stamps the frontmatter), Renames (`Source:` lines do not follow a rename; `check_index.py` reports them), Drive IDs of a vault project (the synchronizer creates the folders, so the IDs come from Drive after the first sync) and Verified synchronizers, a test procedure with a table that starts with Google Drive for desktop, a vault-aware plugin and rclone pending.
- Workflow 6 and the README mirror section offer two paths: in Claude Code, `check_drive.py` with the local `00_INSTRUCTIONS.md` and `01_INDEX.md` and the connector listings, no CSV needed and renames matched by ID; without the connector, the CSV and `check_sync.py` as before. The README compatibility row for the local md mirror says what is verified and what is pending instead of "supported by local scripts".

## [0.3.0] - 2026-09-17

### Added

- Assistant roles (drafter, writer, verifier) recorded in `00_INSTRUCTIONS`, with `init_project.py --drafter/--writer/--verifier`; defaults reproduce v0.2.0.
- The change order as the only path for a change to an existing document: `templates/change-order.md`, Workflow 7.
- The ingest order for bulk ingests, with a transient `_staging/` folder, batch verification and commit by moving: `templates/ingest-order.md`, Workflow 8.
- Per-role instruction blocks in `templates/roles/`.
- `references/assistant-roles.md` with the writer verification test and the status table per assistant.
- `tests/test_templates.py` and `tests/test_docs.py`.
- `check_drive.py`: validates `01_INDEX` against Drive listings saved from the connector (`read_file_content` and `search_files` results; Markdown and `path,drive_id` CSV accepted too). One listing per folder: `--context-listing` and `--sources-listing` are mandatory and bound to their folder, `--project-listing` is optional. Reports missing/stale rows, renames by stable ID, ID mismatches, duplicate titles, nested folders and, with a project listing, the fixed layout, both variants of a canonical file and the canonical IDs.
- `parse_drive_csv_rows` keeps duplicate CSV paths, so `DUPLICATE_TITLE` also applies to CSV listings; `check_sync` keeps the last ID per path as before.
- `common.connector_markdown` and `normalize_connector_markdown`: turn Markdown as the connector returns it (escaped punctuation, indented bullets, bold index header above an empty row, `<!-- end list -->`) into what the parsers expect.
- Connector samples captured on 2026-09-13 under `tests/fixtures/connector/`, anonymised, with the behaviour recorded in `references/drive-connector-behavior.md`.
- SKILL.md: Docs-format maintenance procedure for Claude Code and the manual equivalent for claude.ai; what "paste" means for an index row and a log entry in Docs.

### Changed

- `Connector constraint` in SKILL.md becomes `Write paths`; four new global rules (change orders, ingest orders, read-back after every write, decide the split before writing).
- Setup collects roles; ingest and decision workflows route writes through change orders.
- Connector reference: Markdown-to-Doc conversion joins single-newline lines into one paragraph; two checklist rows recorded as passed on 2026-09-17.
- README compatibility table gains a "Writes in place" column; ChatGPT recorded as a verified writer.
- The Claude and generic instruction blocks become drafter blocks.
- Sample project carries the new sections.
- `create_project()` takes its options after `today` as keyword-only arguments.
- Ingest orders: when a project has no writer assistant, the drafter creates the staged files and the owner checks them against the manifest before the commit.
- `source_reference` tolerates the `Extracted:` tail that Google Docs joins onto the `Source:` line; the extract templates and the example separate the two lines with a blank line.
- `check_index.py` and `check_sync.py` share the canonical-ID, duplicate-row and CSV helpers with the new script; their findings are unchanged.
- Templates document the Docs File cell convention (`10_context/<Drive title>`) and the title-uniqueness rule.
- `_staging/` at the project root is reported by `check_drive.py` as `UNEXPECTED_FILE`: expected while an ingest order is open, a defect otherwise.

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
