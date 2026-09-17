# Docs-format validation through the Drive connector - Design Spec

Date: 2026-09-13
Status: implemented in the branch that carries this file
Depends on: v0.2.0

## 1. Problem

The deterministic checks shipped in v0.2.0 (`check_index.py`, `check_sync.py`) read a local
tree. A Docs-format project has no local tree after setup: the living documents are Google Docs
and the originals are uploaded files. Maintenance therefore depends on the assistant comparing
folder listings with the index by eye, and nothing verifies that the Drive IDs written in
`01_INDEX` are the IDs Drive actually reports. A fictional ID such as `sample-context-id` passes
every existing check.

A second gap: the parsers in `common.py` expect the Markdown that was uploaded, but the connector
returns something else. Underscores come back escaped, the index header comes back bold with an
empty row above it, bullets come back indented, and two consecutive lines of a Doc come back as
one line. `parse_index` on raw connector output produces phantom rows and wrong paths, and
`instruction_drive_ids` finds nothing.

## 2. Verified connector behaviour

Observed on 2026-09-13 in Claude Code desktop with the claude.ai Google Drive connector, against
a throwaway project folder created with the v0.2.0 templates. The samples live under
`tests/fixtures/connector/` with the IDs and the owner anonymised.

| Item | Observed | Consequence |
| --- | --- | --- |
| `read_file_content` result | `{"fileContent": "<markdown>"}` | The script accepts the saved tool result as is. |
| `search_files` with `parentId` | `{"files": [{"id", "title", "mimeType", "parentId", ...}]}`; Docs carry no `fileExtension`, uploaded files do | The script maps `parentId` to the folder names recorded in `00_INSTRUCTIONS`. |
| Underscore in Doc prose | `10\_context`, and inside IDs: `1\_UVWqsl\_s1i...` | Unescape before parsing IDs. |
| Underscore inside a Doc table cell | triple escape: `10\\\_context` | Runs of backslashes before punctuation collapse to the character. |
| Index table of a Doc | empty header row, `:-:` separator, real header as `\*\*File\*\*` | The normalizer rebuilds the block with the canonical header. |
| Bullets | indented two spaces: `  - Project folder: ...` | Dedent list items so `^-` anchored regexes still match. |
| Nested list | `<!-- end list -->` marker between levels | Drop the marker line. |
| Literal pipe inside a cell | `a \| b` (single escape) | Keep `\|` so cell splitting still works. |
| Code spans, code fences, blockquotes | formatting dropped, text kept | Nothing to parse; templates avoid them. |
| Two consecutive lines | joined into one paragraph: `Source: ... (Drive ID: ...) Extracted: ...` | Templates separate `Source:` and `Extracted:` with a blank line; `source_reference` tolerates the joined form. |
| Plain `.md` (no conversion) | `\#` headings, `\-` bullets, two trailing spaces per line, single-escaped underscores | Same normalizer; trailing whitespace stripped. |

## 3. Decisions

| Question | Decision |
| --- | --- |
| Where does the Drive listing come from | Claude saves the connector tool results verbatim to local files. No Drive API, no OAuth, standard library only, as in v0.2.0. Plain Markdown and a `path,drive_id` CSV remain accepted. |
| Identity of a listing | One flag per folder: `--context-listing` and `--sources-listing` are mandatory, `--project-listing` optional. An empty listing means an empty folder. Entries whose `parentId` (JSON) or path (CSV) belongs to another folder are a usage error. The checker therefore cannot report clean while a folder is unchecked. |
| Both variants of a canonical file present | `DUPLICATE_CANONICAL_FILE` (for example `01_INDEX` and `01_INDEX.md`); the ID check for that name waits until one variant is removed. |
| Duplicate paths in a CSV listing | Kept by `parse_drive_csv_rows`, so `DUPLICATE_TITLE` applies to CSV too. `parse_drive_csv`, used by `check_sync.py`, keeps the last ID per path as before. |
| Identity of a Docs file in the index | `10_context/<Drive title>`. Docs have no extension; uploaded originals keep their file name. Titles must be unique inside a folder because the index addresses files by path. |
| Nested folders inside `10_context` or `20_sources` | Reported as `NESTED_FOLDER`. The protocol prescribes flat folders; the check does not follow nested listings. |
| A file renamed in Drive | Reported once as `RENAMED_FILE` (same Drive ID, different title), not as a stale row plus a missing row. |
| Project-root listing | Optional. When present, the canonical files and folders are checked against the IDs in `00_INSTRUCTIONS` and anything outside the fixed layout is `UNEXPECTED_FILE`. |
| Where the normalizer lives | `common.normalize_connector_markdown`, applied only to connector input. Local files are parsed exactly as before. |
| claude.ai and Cowork (no scripts) | The same comparison by hand, with the same finding names, documented in SKILL.md. |
| Vault findings from the same review | Out of scope for this change; listed in section 8. |

## 4. Components

- `common.py`
  - `normalize_connector_markdown(text)`: trailing whitespace, `<!-- end list -->`, list dedent,
    backslash unescape (keeping `\|`), index table rebuild, blank-line collapse.
  - `connector_markdown(raw)`: unwraps a saved `read_file_content` result or accepts Markdown,
    then normalizes.
  - `DriveEntry`, `parse_listing(raw)`, `parse_drive_csv_rows(text)`, `parse_drive_csv(text)`:
    one loader for connector JSON and CSV listings. `check_sync.py` reuses the CSV part.
  - `CANONICAL_LABELS`, `missing_canonical_ids`, `canonical_id_collisions`,
    `duplicate_row_counts`, `duplicate_drive_id_paths`, `first_rows_by_file`: helpers shared by
    `check_index.py` and the new script so the two report identical findings.
  - `source_reference`: tolerates the `Extracted:` tail that Docs joins onto the `Source:` line.
- `check_drive.py`: `check_drive(instructions_text, index_text, listings)` takes one `Listing`
  per folder and returns findings; `main` reads the files behind `--context-listing`,
  `--sources-listing` and `--project-listing`, unwraps envelopes, and turns malformed input,
  a folder without a recorded ID and foreign entries into exit 2.

## 5. Findings and exit codes

| Finding | Meaning |
| --- | --- |
| `MISSING_PROJECT_ID` | Drive IDs section missing, or a canonical ID empty/TODO-ID |
| `DUPLICATE_PROJECT_ID` | a canonical ID collides with another one or with an index row |
| `DUPLICATE_ROW` | the same path listed more than once in the index |
| `MISSING_DRIVE_ID` | an index row still carries TODO-ID or an empty ID |
| `DUPLICATE_DRIVE_ID` | one populated Drive ID on several rows |
| `NESTED_FOLDER` | a folder inside `10_context` or `20_sources` |
| `DUPLICATE_TITLE` | two Drive entries share a path |
| `MISSING_CANONICAL_FILE` | a root listing lacks one of the five fixed entries |
| `DUPLICATE_CANONICAL_FILE` | both variants of a fixed entry exist, such as `01_INDEX` and `01_INDEX.md` |
| `UNEXPECTED_FILE` | a root entry outside the fixed layout |
| `RENAMED_FILE` | an index row's Drive ID now carries a different title |
| `MISSING_ROW` | a Drive file without an index row |
| `STALE_ROW` | an index row without a Drive file |
| `ID_MISMATCH` | index and Drive disagree on the ID of the same path |

Exit `0` clean, `1` findings, `2` usage error (unreadable file, malformed listing, a listed
folder without an ID in `00_INSTRUCTIONS`, entries that belong to another folder, or a JSON
document without `fileContent`).

## 6. Workflow changes

- Workflow 3 (ingest): after the owner pastes the index row, run `check_drive.py` in Claude Code
  so the paste is verified against the real IDs instead of by re-reading alone.
- Workflow 5 (maintenance): Docs variant with the exact save-and-run procedure for Claude Code
  and the equivalent manual comparison for claude.ai.
- Connector constraint: what "paste" means in Docs. An index row is a table row with five cells,
  not pasted Markdown. A log entry title is a Heading 3 paragraph, which reads back as `###`.
- Global rules: titles unique per folder; each metadata line of a Doc-authored document is its
  own paragraph.

## 7. Template changes

- `source-extract.md`, `source-extract-vault.md`, the example extract: a blank line between the
  `Source:` and `Extracted:` lines.
- `01_INDEX.md`: the File cell convention for Docs.
- `00_INSTRUCTIONS.md`: title uniqueness rule.

## 8. Out of scope, recorded for follow-up

- Vault mode: `drive_id` in frontmatter and the index row are never compared, and
  `build_index.py --write` replaces the row ID with the frontmatter value silently.
- Vault mode: `BROKEN_LINK` is reported for wikilinks to non-Markdown files (`[[contract.pdf]]`,
  `![[image.png]]`) and for the `[[wikilinks]]` placeholder in `source-extract-vault.md`.
- `check_sync.py` could accept the connector JSON through the same loader; it keeps the CSV
  contract in this change.
- The three write-side checklist items that need a second account or a browser edit remain
  pending in `references/drive-connector-behavior.md`.

## 9. Testing

- Fixtures: the anonymised connector samples (two documents, a plain `.md`, a format probe with
  the awkward cases, three listings, and the index as it looks after the owner pastes the IDs).
- Unit tests for the normalizer, including a property test that it is idempotent on its own
  output.
- `check_drive` tests for every finding, the CSV path, the root listing, the listing errors and
  the exit codes; the clean fixture project must exit 0.
- Existing suites unchanged in behaviour: `check_index` and `check_sync` keep their outputs while
  sharing the extracted helpers.

## 10. Review round (2026-09-13)

The maintainer asked for three changes before merging; all three are in this design:

1. Explicit, mandatory listings per content folder, so an empty listing keeps its identity and a
   folder can never go unchecked (section 3, "Identity of a listing").
2. Both variants of a canonical file reported instead of silently taking the first one
   (`DUPLICATE_CANONICAL_FILE`).
3. Duplicate paths preserved in CSV listings so `DUPLICATE_TITLE` applies there too.
