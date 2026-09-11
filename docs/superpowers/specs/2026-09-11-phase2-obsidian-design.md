# Phase 2 - Obsidian vault as the home of a shared project

Date: 2026-09-11
Status: design outline, approved direction (Edgar), not yet implemented
Depends on: phase 1 (`2026-09-11-drive-shared-projects-design.md`) shipped and verified

## 1. Goal

A shared project folder lives inside an Obsidian vault as plain `.md` files.
Google Drive mirrors that subfolder, so every assistant with Drive access
reads the same files while the owner edits them in Obsidian with links,
backlinks, graph and search. One source of truth: the vault.

Phase 1 already supports the `md` format. Phase 2 makes that format
first-class for a vault: naming, frontmatter, links, sync and the maintenance
checks that a vault needs.

## 2. Decisions taken

| Question | Decision |
| --- | --- |
| Relationship vault / Drive | The project folder is a subfolder of the vault. Drive syncs that subfolder. |
| Source of truth | The vault (`.md` on disk, optionally under git). Drive is a mirror. |
| Target vault | Generic. Edgar's vault is the worked example in the docs. |
| Document format | `.md` only. No Google Docs inside a vault project. |
| Assistants | Any assistant with a Drive connector reads the folder (see phase 1 README, "Works with any assistant"). |

## 3. Non-goals

- Two-way merge of concurrent edits made in Drive by other people. In phase
  2 other members edit through the vault owner (they propose via the log, or
  they also run Obsidian on the synced folder). Concurrent Docs editing is a
  phase 1 feature and stays there.
- Obsidian plugin development. Phase 2 uses existing sync mechanisms and the
  phase 1 scripts.
- Publishing the vault. Only the project subfolder is shared.

## 4. Sync mechanism (to be chosen during phase 2 brainstorming)

| Option | How | Pros | Cons |
| --- | --- | --- | --- |
| A. Google Drive for desktop | The vault (or the project subfolder) sits inside the Drive-synced folder on disk. | Zero config beyond the client; works for any file. | Whole-vault sync unless the project folder is symlinked or the vault is inside Drive; the desktop client can create conflict copies. |
| B. Obsidian plugin Remotely Save | Community plugin syncing the vault to Google Drive (or S3, WebDAV). | Vault-aware, selective folders, runs inside Obsidian. | Third-party plugin, OAuth setup per person, sync granularity is the vault. |
| C. rclone one-way push | `rclone sync <vault>/<project> gdrive:<project>` on a schedule or a git hook. | Deterministic, scriptable, one direction. | Needs rclone and its OAuth; not for non-technical members. |

Recommendation to test first: A with the vault living inside the Drive folder,
because it needs no code and matches how a non-technical duo would work.
C is the fallback when the owner wants git as the master and Drive as a
published copy.

## 5. What changes in the skill

- `SKILL.md`: a "vault" variant of Workflow 1 (Setup). Fifth setup question
  when format is `md`: "Does this project live in an Obsidian vault?" If yes,
  the folder is created inside the vault path and Drive sync is confirmed
  before the IDs are collected.
- Frontmatter: every `10_context` extract gets YAML frontmatter
  (`title`, `source`, `drive_id`, `updated`, `owner`) so Obsidian Dataview
  and the phase 1 scripts read the same metadata. `build_index.py` learns to
  read `drive_id` and `title` from frontmatter before falling back to the
  first heading.
- Links: extracts may use `[[wikilinks]]` between context files. Drive
  connectors read them as plain text, which is acceptable. The index remains
  the map for assistants; wikilinks are for humans.
- `check_index.py`: two new findings, `BROKEN_LINK` (a `[[wikilink]]` whose
  target does not exist in the project folder) and `MISSING_FRONTMATTER`
  (a context file without the required keys).
- Sync check: a `check_sync.py` script (stdlib) that compares the local tree
  with a Drive listing exported to CSV (or, in Claude Code, with the
  connector's folder listing pasted by Claude) and reports files present on
  one side only. Exit code is the verdict, as in phase 1.
- Templates: `10_context` extract template gains the frontmatter block; a
  `vault-setup.md` reference explains the three sync options and how to
  exclude `.obsidian/` from the shared folder.

## 6. Worked example: Edgar's vault

Vault: `Documentos\Eduardo's Vault`. Proposed placement: a top-level folder
`Projects/` holding one subfolder per shared project, each with the phase 1
layout. Only `Projects/<name>/` is synced to Drive. Domain hubs (`AI`,
`Finance`, `Business`) link into project extracts with wikilinks; extracts
never link out to private vault pages, so nothing private leaks through the
synced folder.

## 7. Open questions for the phase 2 brainstorming

1. Which sync option (A, B, C) is tested first, and on which machine.
2. Whether `.obsidian/` config is excluded from the shared folder (default
   yes) and how each sync option does it.
3. Frontmatter key names, fixed before touching `build_index.py`.
4. Whether members without Obsidian edit in Drive at all in phase 2, or only
   read.

## 8. Order of work

1. Brainstorm the open questions (one session).
2. Manual test of the chosen sync option with the phase 1 example project.
3. Spec update, then plan: frontmatter support in `build_index.py`, new
   findings in `check_index.py`, `check_sync.py`, templates, SKILL.md vault
   variant, README section.
4. Verify with the Drive connector that the synced `.md` files are read by
   at least one assistant other than Claude.
