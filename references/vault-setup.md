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

Every script skips a file or folder whose name starts with a dot, locally and in Drive listings alike, so a synced `.gitkeep` or `.obsidian/` is never a finding. The same rule means nothing checks that `.obsidian/` stayed outside the project.

## Sync options

### A. Google Drive for desktop

Best default for non-technical setups. Put the project folder inside a Drive-synced location, or place the vault there if that trade-off is acceptable. Watch for conflict copies if two machines edit the same file concurrently.

### B. Vault-aware sync plugin

Useful when selective vault sync matters, for example Remotely Save; check that your version syncs to Google Drive. This introduces a third-party plugin and its own OAuth/conflict behavior, so verify it before treating the mirror as reliable.

### C. rclone one-way publish

Best when git/local files are clearly authoritative and Drive is only a published mirror. Example pattern:

```text
rclone sync --track-renames <vault>/Projects/<project> gdrive:<project>
```

Without `--track-renames`, rclone deletes a renamed file on Drive and uploads it again as a new file: the new copy gets a new Drive ID, and the `drive_id` in the frontmatter and in the index points at a file that no longer exists. With the flag, rclone matches the renamed file by size and hash and moves it on the server instead, which in Drive renames the same file. It cannot match a file that was renamed and edited between two runs, because the hash changed; sync after renaming and before editing. Whether the ID survives is recorded under Verified synchronizers once tested.

One-way sync is easier to reason about than two-way concurrent editing.

## Obsidian settings

- Files and links, "Automatically update internal links": on. Renaming a note in Obsidian then rewrites the wikilinks that point to it.
- Files and links, "Default location for new attachments": a folder outside the shared project. A pasted image then never lands in `10_context` without an index row; an image a note needs is copied into `20_sources` and indexed, as described under Wikilinks and embeds. The options that store attachments next to the note would drop them into `10_context`, or into a subfolder there, which is a `NESTED_FOLDER`.
- No Excalidraw drawings or Canvas files in `10_context`. They are drawing data, not context an assistant can read, a drawing soon passes the size cap, and an Excalidraw file carries its own frontmatter and fails `MISSING_FRONTMATTER`. Keep them outside the project, or in `20_sources` when they are evidence.
- A template that stamps the frontmatter on every new note in `10_context`, kept outside the project. With the core Templates plugin:

```yaml
---
title: "{{title}}"
source: ""
drive_id: "TODO-ID"
updated: "{{date:YYYY-MM-DD}}"
owner: ""
---
```

With Templater, `<% tp.file.title %>` and `<% tp.date.now("YYYY-MM-DD") %>` replace the two placeholders. `check_index.py` reports `MISSING_FRONTMATTER` while `source` or `owner` is empty, and `MISSING_DRIVE_ID` until the ID the sync assigns replaces `TODO-ID`.

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

`check_index.py` reports `MISSING_FRONTMATTER` if a required key is absent/empty, `MISSING_DRIVE_ID` while `drive_id` is still `TODO-ID`, and `ID_MISMATCH` when `drive_id` disagrees with the file's index row. `build_index.py` lets the frontmatter ID win and says so on stderr, so fix whichever side is wrong before writing the index.

## Renames

Obsidian rewrites wikilinks when a file is renamed, but not plain text. After a file in `20_sources` is renamed, the `Source:` line of every extract that cites it, and the `source` key of their frontmatter, still name the old path; `check_index.py` reports `INVALID_SOURCE_REFERENCE` ("Source path does not exist") for each of them. Search the project for the old name and fix those lines by hand.

A renamed note keeps its index row through its frontmatter `drive_id` when `build_index.py --write` runs. A renamed original in `20_sources` has no frontmatter, so its old row turns stale and the new name gets a `TODO-ID` row; copy the Drive ID over from the old row if the sync kept it, which the Drive check below tells.

## Wikilinks and embeds

`[[wikilinks]]` are for human navigation. Assistants still use 01_INDEX as the canonical routing map. Links must resolve inside the shared project; `check_index.py` reports `BROKEN_LINK` otherwise.

`check_index.py` resolves a link the way Obsidian does: against every file in `10_context`, `20_sources` and the three root files, by path or by file name, ignoring case. A note also resolves without `.md`; any other file needs its extension, as in `[[informe.pdf]]`. Text inside inline code or a code block is not a link.

An embed such as `![[figura.png]]` follows the same rule. An image or PDF that a note embeds is an original, so it lives in `20_sources` with its own index row and Drive ID, and a reader on Drive opens it by that ID. An image pasted into a note by accident is reported as a broken embed until it is moved there or the embed is removed.

## Drive IDs of a vault project

In a vault the synchronizer creates the Drive folders and files, so the IDs cannot be read from create results as in Workflow 1. After the first sync, take the project folder ID from its Drive URL and list that folder by `parentId`: the listing gives the IDs of `10_context`, `20_sources`, `01_INDEX.md` and `90_LOG.md` for the Drive IDs section of `00_INSTRUCTIONS.md`. The listings of the two content folders give the ID of every file, for its index row and, for a note, its frontmatter.

## Sync verification

### In Claude Code, with the Drive connector

List the project folder, `10_context` and `20_sources` with `parentId = '<folder ID>'` and save each result verbatim, as in the Docs-format maintenance of Workflow 5. Then check the local instructions and index against them:

```bash
python scripts/check_drive.py --instructions ./project/00_INSTRUCTIONS.md --index ./project/01_INDEX.md \
  --context-listing 10_context.json --sources-listing 20_sources.json --project-listing project.json
```

No CSV is needed. The Drive titles of synced `.md` files keep their extension, so they match the File cells. A rename that kept its Drive ID shows as `RENAMED_FILE` while the index still has the old name, and a file the sync re-created shows as `ID_MISMATCH` against the ID in the index.

### Without the connector

Create a UTF-8 CSV with `path,drive_id` columns from a Drive folder listing, then run:

```bash
python scripts/check_sync.py --root ./project --drive-csv ./drive-listing.csv
```

Findings:

- `LOCAL_ONLY`: local file is absent from Drive listing.
- `DRIVE_ONLY`: Drive file is absent locally.
- `ID_MISMATCH`: both exist but populated IDs disagree.
- `ID_MISSING`: both exist but only one side records a Drive ID.

`00_INSTRUCTIONS.md` has no self-ID by design, so sync validation compares its presence but not its identity.

## Verified synchronizers

Whether a synchronizer keeps the Drive ID when a file is renamed decides whether vault mode works with it. Run this once per synchronizer and environment, as the connector checklist is run once per environment, and record the result below:

1. Create the project inside the vault with `init_project.py --vault` and let the synchronizer publish it.
2. Fill the Drive IDs as described above; `check_index.py` and the Drive check come back clean.
3. Rename a note in Obsidian, run `build_index.py --write` and wait for the sync.
4. Run `check_index.py` and the Drive check. Clean means the Drive ID survived the rename; `ID_MISMATCH` means the synchronizer re-created the file under a new ID.

| Synchronizer | Environment | Date | Keeps the Drive ID on rename | Result |
| --- | --- | --- | --- | --- |
| Google Drive for desktop | pending | pending | pending | pending |
| Remotely Save or another vault-aware plugin | pending | pending | pending | pending |
| rclone sync --track-renames | pending | pending | pending | pending |
