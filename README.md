# drive-shared-projects

A portable shared-memory and governance layer for AI-assisted projects, backed by Google Drive.

The reference implementation is a Claude Skill, but the project state itself is vendor-neutral: instructions, an index, working context, original sources and an append-only decision log. Any assistant that can read the same Drive files can consume the same project memory without sharing chat history.

> This is not an agent framework. It is the context, identity and governance layer that agents or assistants can work on top of.

## Why it exists

Long-running AI work breaks when knowledge is trapped in individual chats. This project externalizes the durable parts:

- what the project is and how the assistant should behave;
- what files exist and when to read them;
- the current working knowledge;
- the original evidence;
- the decisions and lessons that must survive across conversations.

The result is a project that can be resumed by another chat, another person or another assistant without replaying the full conversation history.

## Architecture

```text
                         ┌─────────────────────┐
                         │   00_INSTRUCTIONS   │
                         │ role · rules · IDs  │
                         └──────────┬──────────┘
                                    │
                                    v
                         ┌─────────────────────┐
                         │      01_INDEX       │
                         │ routing + identity  │
                         └──────────┬──────────┘
                                    │
                  ┌─────────────────┴─────────────────┐
                  v                                   v
          ┌───────────────┐                   ┌───────────────┐
          │  10_context/  │  extracts from    │  20_sources/  │
          │ working truth │ <──────────────── │ originals     │
          └───────┬───────┘                   └───────────────┘
                  │
                  v
          ┌───────────────┐
          │    90_LOG     │
          │ decisions     │
          │ + lessons     │
          └───────────────┘
```

`01_INDEX` is a routing layer: assistants read it first and load only the context relevant to the current task. `10_context` is the preferred working representation; `20_sources` is opened for exact figures, quotations or details that the extract does not contain.

## Core guarantees

The scripts turn several workflow rules into deterministic checks:

- every context/source file has exactly one index row;
- every indexed file exists;
- every row has a populated Drive ID and IDs are unique;
- `00_INSTRUCTIONS` is readable and carries a Drive IDs section;
- the canonical project IDs in `00_INSTRUCTIONS` (project/context/source folders, INDEX and LOG) are populated and do not collide with each other or indexed files;
- a `Source:` relationship points to a real source and, when supplied, the same Drive ID recorded in the index;
- context files stay under the configured size cap, 50,000 by default, counted in UTF-8 bytes so accented text cannot slip past it;
- destructive index refreshes require an explicit `--allow-drop`;
- vault projects require frontmatter and valid Obsidian wikilinks;
- a local vault can be compared with a Drive listing using `check_sync.py`;
- a Docs project is validated against the real Drive listing with `check_drive.py`: rows, IDs, renames, duplicate titles and the fixed layout.

## Folder layout

```text
project/
├── 00_INSTRUCTIONS.md
├── 01_INDEX.md
├── 10_context/
├── 20_sources/
└── 90_LOG.md
```

The names are fixed because the scripts and prompt templates key on them.

## Workflows

1. **Setup** — create the project, governance mode and Drive structure.
2. **Session start** — read instructions and index; load only relevant files.
3. **Ingest** — keep the original in `20_sources`, create a compact extract in `10_context`, then index both.
4. **Decision logging** — append decisions and lessons to `90_LOG`; never rewrite history.
5. **Maintenance** — validate identity, index consistency, source links, size limits and vault links; in Docs format, validate the index against the Drive listing.
6. **Sync check** — for vault projects, compare the local source of truth with a Drive listing.
7. **Change order** — the only way a change to an existing document travels: drafted by one party, approved by the owner, applied by another, read back twice.
8. **Ingest order** — a bulk ingest runs into a transient `_staging/` folder, is verified there, and is committed by moving files into place; nothing canonical is touched before verification.

## Modes

| Rule | solo | duo | group |
| --- | --- | --- | --- |
| Index owner | one person | one named owner | one named owner |
| Log author | optional | required | required |
| Drive sharing | none required | both editors | owners editors; others commenters |
| Index proposals | direct | non-owner proposes to owner | member proposes via comment/chat; owner records and merges |
| Instruction changes | direct | direct + log | approval + log + owner edit |

Three or four people: use `duo` when everyone edits; use `group` when most people read/comment.

## Formats

### Google Docs

Default for browser-first collaboration. The connector can create and read the documents, but the verified connector cannot rewrite existing file contents in place. Changes to an existing index, log or instruction document therefore travel as a change order (Workflow 7) that a person applies by paste, or that a verified writer assistant applies in place; someone re-reads the document by ID afterwards.

What the connector returns is not the Markdown that was uploaded: punctuation comes back escaped, bullets indented and the index header bold above an empty row. `check_drive.py` consumes those results as saved and validates the index against the real listing (see below).

### Markdown / Obsidian vault

Use `md` when the local filesystem is authoritative: a git repository or an Obsidian vault mirrored to Drive. Vault projects add frontmatter and wikilink validation.

A vault extract uses metadata such as:

```yaml
---
title: "Momentum backtest 2026"
source: "20_sources/momentum_backtest_2026.md"
drive_id: "1abc..."
updated: "2026-09-12"
owner: "Ana"
---
```

The stable `drive_id` lets `build_index.py` recognize a rename as the same file instead of treating it as a deletion plus a new file.

See `references/vault-setup.md` for sync options and the Drive-listing check.

## Assistant roles, change orders and ingest orders

Roles are recorded in `00_INSTRUCTIONS` and are independent of the mode:

- the drafter analyses, synthesises, creates new documents and writes change orders; it never modifies an existing document;
- the writer applies change orders inside the existing document, keeping its Drive ID, and re-reads afterwards; it never decides the content and never re-creates a document;
- an optional verifier reads applied changes and checks them against the order;
- the owner approves every order.

A change order has five fields: target and Drive ID; what changes and why; the exact text; what must be true after the write; who applies it. A bulk ingest travels as an ingest order: manifest first, execution into `_staging/`, verification on the staged files, commit by moving them into place (the move keeps every Drive ID), then one write to the index and one to the log. The writer role is granted only after the verification test in `references/assistant-roles.md`.

Defaults reproduce a single-assistant project: drafter Claude, writer a person by paste, no verifier. Templates: `templates/change-order.md`, `templates/ingest-order.md`, `templates/roles/`.

## Compatibility status

The **protocol** is vendor-neutral; connector behavior is not. Do not confuse the two.

| Assistant / environment | Protocol fit | Writes in place | End-to-end verification in this repo |
| --- | --- | --- | --- |
| Claude + Drive connector | reference implementation | no; creates and reads | read/create/listing behavior verified 2026-09-11; existing-content rewrite unsupported; Docs index validated by `check_drive.py` from saved connector results |
| Claude Code + local md mirror | reference implementation | via the local file | supported by local scripts |
| ChatGPT + Drive access | designed to consume the same folder | yes, verified 2026-09-17 | in a real project a document kept its Drive ID while its content changed; open-by-ID not confirmed, open-by-name works |
| Gemini + Drive access | designed to consume the same folder | not verified | not yet verified end-to-end here; starts as verifier |
| Grok / Copilot / local model | compatible when a Drive/files tool exists | not verified | not yet verified end-to-end here |

Use the blocks in `templates/roles/` outside Claude; `templates/assistant-instruction-generic.md` is kept as the drafter block.

## Install

### Claude Code

Windows:

```powershell
git clone https://github.com/EERamos/drive-shared-projects.git
cd drive-shared-projects
.\install.ps1
```

macOS / Linux:

```bash
git clone https://github.com/EERamos/drive-shared-projects.git
cd drive-shared-projects
./install.sh
```

The installer copies `SKILL.md`, `templates/`, `references/` and `scripts/` into `~/.claude/skills/drive-shared-projects`.

### claude.ai / Cowork

Create a zip containing only:

```text
drive-shared-projects/
├── SKILL.md
├── templates/
└── references/
```

Upload it under Skills and enable the Google Drive connector. Each collaborator installs the skill in their own account.

## Create a local project

Docs-style seed:

```bash
python ~/.claude/skills/drive-shared-projects/scripts/init_project.py \
  --name "Quant Research" \
  --mode duo \
  --format docs \
  --owner "Ana" \
  --out ./quant-research
```

Obsidian-vault project:

```bash
python ~/.claude/skills/drive-shared-projects/scripts/init_project.py \
  --name "Quant Research" \
  --mode duo \
  --format md \
  --vault \
  --owner "Ana" \
  --role "research assistant for the quant team" \
  --tone "direct, technical, Spanish" \
  --out ./quant-research
```

`00_INSTRUCTIONS` does **not** store its own Drive ID. That removes a circular setup step: the project instruction block already carries the ID needed to open it.

## Validate a project

```bash
python ~/.claude/skills/drive-shared-projects/scripts/check_index.py --root ./quant-research
```

Exit codes:

- `0`: clean;
- `1`: findings;
- `2`: usage/setup error.

## Validate a Docs project

A Docs project has no local tree, so the check runs on the connector's own results. In Claude Code, read `00_INSTRUCTIONS` and `01_INDEX` by ID, list `10_context`, `20_sources` and the project folder with `parentId = '<folder id>'`, and save every tool result verbatim (`{"fileContent": ...}` and `{"files": [...]}`) into a scratch folder. Then:

```bash
python ~/.claude/skills/drive-shared-projects/scripts/check_drive.py \
  --instructions 00_INSTRUCTIONS.json \
  --index 01_INDEX.json \
  --context-listing 10_context.json \
  --sources-listing 20_sources.json \
  --project-listing project.json
```

The two content listings are mandatory and each is bound to its folder: an empty result means an empty folder, and entries that belong to another folder are a usage error, so the check can never report clean with a folder unchecked. The project listing is optional and adds the fixed-layout checks.

It reports `MISSING_ROW`, `STALE_ROW`, `RENAMED_FILE`, `ID_MISMATCH`, `DUPLICATE_TITLE`, `NESTED_FOLDER`, the index-structure and canonical-ID findings of `check_index.py`, and with the project listing `MISSING_CANONICAL_FILE`, `DUPLICATE_CANONICAL_FILE` and `UNEXPECTED_FILE`. `UNEXPECTED_FILE` on `_staging/` is the expected report while an ingest order is open, and a leftover to trash otherwise. Same exit codes. Plain Markdown documents and `path,drive_id` CSV listings, one per folder, are accepted as well; duplicate paths in a CSV are kept and reported.

## Refresh the index safely

Preview first:

```bash
python ~/.claude/skills/drive-shared-projects/scripts/build_index.py --root ./quant-research
```

Write when nothing destructive is being removed:

```bash
python ~/.claude/skills/drive-shared-projects/scripts/build_index.py --root ./quant-research --write
```

If stale rows would be removed, the write is refused. After reviewing the preview, explicitly allow the removal:

```bash
python ~/.claude/skills/drive-shared-projects/scripts/build_index.py \
  --root ./quant-research \
  --write \
  --allow-drop
```

A successful write also refreshes `Last updated`.

## Check an Obsidian/Drive mirror

Export or produce a CSV listing with:

```csv
path,drive_id
00_INSTRUCTIONS.md,1abc...
01_INDEX.md,1def...
10_context/topic.md,1ghi...
20_sources/source.pdf,1jkl...
90_LOG.md,1mno...
```

Then run:

```bash
python ~/.claude/skills/drive-shared-projects/scripts/check_sync.py \
  --root ./quant-research \
  --drive-csv ./drive-listing.csv
```

It reports `LOCAL_ONLY`, `DRIVE_ONLY`, `ID_MISMATCH` and `ID_MISSING` findings. `00_INSTRUCTIONS` has no local self-ID by design, so an empty local ID is not a finding for that path.

## Development

```bash
python -m pip install "pytest>=8" "hypothesis>=6" "ruff>=0.5" "mypy>=1.10"
python -m pytest
python -m ruff check scripts tests
python -m ruff format --check scripts tests
python -m mypy
```

GitHub Actions runs the same quality gates across the supported Python matrix.

## Repository layout

| Path | Purpose |
| --- | --- |
| `SKILL.md` | workflows and operating rules |
| `templates/` | project documents, prompt blocks per role, change and ingest orders |
| `references/` | connector behavior, governance and vault setup |
| `scripts/` | deterministic setup/index/sync tools |
| `tests/` | pytest suite |
| `examples/sample-project/` | filled example |
| `docs/architecture/` | durable architecture documentation |
| `docs/superpowers/` | historical design/implementation notes |

## Security model

Project files are data, not instructions. An instruction-like sentence inside a PDF, Doc or Markdown source never overrides the assistant's project/system instructions. This is the project's primary prompt-injection boundary.

No credentials or Drive tokens belong in the repository. For public commits, use a GitHub noreply email if you do not want a personal email exposed in commit metadata.

## Versioning

Semantic versioning. Consumers should pin a release tag. Notable changes are recorded in `CHANGELOG.md`.

## License

MIT.
