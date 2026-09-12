# Obsidian vault setup

Vault mode makes a local Markdown project the source of truth and treats Google Drive as a mirror for assistants and collaborators.

## Source of truth

- Local vault/project folder: authoritative.
- Google Drive: mirrored copy.
- `01_INDEX.md`: identity/routing map.
- `drive_id` frontmatter: stable identity across local renames.

Do not edit the same Markdown file concurrently in Drive and the vault unless your sync tool has a conflict strategy you understand.

## Recommended folder

```text
<your vault>/Projects/<project-name>/
```

Keep `.obsidian/` outside the shared project folder. Shared extracts may link to other files inside the project, but should not link to private notes elsewhere in the vault.

## Sync options

### A. Google Drive for desktop

Best default for non-technical setups. Put the project folder inside a Drive-synced location, or place the vault there if that trade-off is acceptable. Watch for conflict copies if two machines edit the same file concurrently.

### B. Vault-aware sync plugin

Useful when selective vault sync matters. This introduces a third-party plugin and its own OAuth/conflict behavior, so verify it before treating the mirror as reliable.

### C. rclone one-way publish

Best when git/local files are clearly authoritative and Drive is only a published mirror. Example pattern:

```text
rclone sync <vault>/Projects/<project> gdrive:<project>
```

One-way sync is easier to reason about than two-way concurrent editing.

## Frontmatter

Every `10_context/*.md` file in a vault project must include:

```yaml
---
title: "Readable title"
source: "20_sources/original.pdf"
drive_id: "1abc..."
updated: "2026-09-12"
owner: "Ana"
---
```

`check_index.py` reports `MISSING_FRONTMATTER` if a required key is absent/empty.

## Wikilinks

`[[wikilinks]]` are for human navigation. Assistants still use 01_INDEX as the canonical routing map. Links must resolve inside the shared project; `check_index.py` reports `BROKEN_LINK` otherwise.

## Sync verification

Create a UTF-8 CSV with `path,drive_id` columns from a Drive folder listing, then run:

```bash
python scripts/check_sync.py --root ./project --drive-csv ./drive-listing.csv
```

Findings:

- `LOCAL_ONLY`: local file is absent from Drive listing.
- `DRIVE_ONLY`: Drive file is absent locally.
- `ID_MISMATCH`: both exist but populated IDs disagree.

`00_INSTRUCTIONS.md` has no self-ID by design, so sync validation compares its presence but not its identity.
