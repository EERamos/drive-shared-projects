# Assistant roles and change orders (v0.3.0)

Date: 2026-09-17. Status: approved design, pending implementation.

## 1. Goal

v0.2.0 assumes one assistant (Claude) whose Drive connector can create and read files but cannot rewrite an existing one, so every change to an existing document goes through a person who pastes it. A pilot on a real project (2026-09-16/17) showed a second assistant that can edit a Google Doc in place, and a third one that is useful for capture and verification. v0.3.0 makes that division of labour part of the protocol without changing the folder layout, the scripts' checks or the human governance modes:

- name the assistant roles (drafter, writer, verifier) and record who holds each in `00_INSTRUCTIONS`;
- make the change order the only way a change to an existing document travels between a drafter and a writer;
- grant the writer role only after a documented verification test;
- fold in three documentary lessons from the pilot.

A v0.2.0 project keeps validating unchanged. The defaults of every new option reproduce v0.2.0 behaviour exactly.

## 2. Decisions taken

- Roles are a property of the project, recorded in `00_INSTRUCTIONS`, independent of the human mode (`solo`, `duo`, `group`). The mode says who decides; the roles say which assistant drafts, which one writes and which one verifies.
- Three assistant roles only: drafter, writer, verifier. There is no "capturer" role: anyone may leave an original in `20_sources`; indexing it goes through a change order like any other change.
- The change order is a chat artifact, not a project file. It has five mandatory fields. It is drafted by one party and applied by another, never both by the same one.
- Human approval governs. The writer applies what the index owner approved; in `group` mode, an order that touches `01_INDEX` or `90_LOG` needs an owner's approval. The tables in `references/modes.md` do not change.
- A writer role is granted only after the writer verification test in `references/assistant-roles.md` passes. Verification is per assistant and per environment; protocol compatibility and verified write paths remain separate claims.
- Never replace an existing document by re-creating it: the Drive ID changes and every reference breaks. This was already a rule; it becomes a global rule and a line in every role block.
- One open change order per document. There is no conflict detection between two writers; the last write wins.
- Defaults: drafter `Claude`, writer `a person, by paste`, verifier `none`.
- Creating a new document never needs a change order; indexing it does. The drafter creates analysis and synthesis documents directly and hands over a change order for the index row and the log entry.
- A bulk ingest (more than one source, or any ingest run by a writer assistant) travels as an ingest order: manifest first, execution into a transient `_staging/` folder at the project root, verification on the staged files, commit by moving them into place, then one write to `01_INDEX` and one to `90_LOG`. Moving keeps the Drive ID and is an operation the Claude connector can perform, so the drafter commits and the writer never touches the canonical tree before verification. If verification fails, `_staging/` is trashed and the manifest is corrected; nothing canonical is rewritten.
- When the project has no writer assistant, the drafter creates the staged files of an ingest order itself, since creating is not the constrained operation, and the owner checks them against the manifest before the commit. Recorded after the final review of the branch.
- `check_index.py` and `build_index.py` scan only `10_context` and `20_sources` and never see `_staging/`; `check_drive.py` (main, PR #3) with a project listing reports it as `UNEXPECTED_FILE`, which is the expected finding while an ingest order is open and a defect otherwise. A clean project has no `_staging/` folder. No script change.
- One open ingest order at a time, like one open change order per document.
- No client data enters the repository. Evidence from the pilot is recorded generically ("a real project", date, what was observed), never with names, figures or Drive IDs of the client.

## 3. Non-goals

- A change-order mailbox inside the project folder (a `30_orders/` directory) and any change to the fixed layout.
- A script that validates change orders.
- Changes to `check_index.py`, `build_index.py`, `check_sync.py` or `common.py`. The new sections of `00_INSTRUCTIONS` are prose that no script parses, and `_staging/` lives outside the scanned directories.
- A script change for `_staging/`: `check_drive.py` already reports it, and that is the desired behaviour; in md format its absence is checked by listing.
- Changes to the human modes or their sharing rules.
- Changes to the md/vault write path beyond wording: in md format the writer is still whoever edits the local mirror.
- Granting Gemini or any other assistant the writer role. They start as verifier or drafter until they pass the test.

## 4. Concepts

### 4.1 Roles

- Drafter: reads, analyses and synthesises; creates new analysis documents directly; detects what must change in existing ones and writes the change order with the exact replacement text. Never writes to an existing document. Verifies applied changes and ingest batches independently by re-reading by ID, and commits a verified ingest batch by moving its files into place.
- Writer: applies a change order inside the existing document, keeping its Drive ID, and re-reads the document afterwards. Does not decide the content: if the order looks wrong or does not fit, returns it with the objection instead of applying part of it. If it notices something that should change, drafts a change order and hands it over without applying it. In Docs format with no assistant writer, the writer is a person who pastes with Paste from Markdown; in md format, whoever edits the local mirror.
- Verifier: reads an applied change and checks it point by point against the order's criteria. Optional. A verifier with no verified write path never writes to `10_context`, `01_INDEX` or `90_LOG`.
- Owner: the human index owner from the mode. Approves every change order before it is applied.

### 4.2 Change order

Five fields, always all five:

1. Target: the document and its Drive ID.
2. What changes and why: two or three lines, with the evidence or the source behind it.
3. Exact text: complete and ready to paste, not a description of it. When a section is replaced, the order names the section boundaries.
4. What must be true after the write: criteria a read-back can confirm (rows, sections present, control figures, ID unchanged).
5. Who applies it, and whether it needs a `90_LOG` entry.

Rules: the drafter does not apply; the writer does not decide; the owner approves before anything is applied; two verifications follow every write, the writer's immediate read-back and the drafter's independent one; only orders that carry a project decision are recorded in `90_LOG`.

### 4.3 Write paths

- A person pastes (Docs) or edits the local mirror (md), then someone re-reads by ID.
- A verified writer assistant applies a change order in place, then re-reads.
- Re-creating a document is never a write path.

### 4.4 Ingest orders and new documents

Creating a document is not the constrained operation; rewriting one is. Two consequences:

- The drafter creates new analysis and synthesis documents directly, then hands over a change order for their index row and log entry. Creating needs no order; indexing does.
- A bulk ingest is the most expensive thing to undo, so it is run so that nothing canonical is touched until it is verified. It travels as an ingest order in five steps:

1. Manifest, with no writes: sources to copy (origin and Drive ID, target subfolder under `20_sources`), exclusions with the reason (an original that is personal data of a natural person is excluded unless the owner says otherwise), extracts to create (topic, file name, the sources each draws on, who synthesises it), and the exact index rows and the exact `90_LOG` entry the batch will add. The owner approves the manifest.
2. Execution into `_staging/`, a transient folder at the project root. The writer assistant creates the copies and the extracts there when the project has one; otherwise the drafter creates them and the owner checks them against the manifest before the commit. Never in `10_context` or `20_sources`. Before copying, it lists the target and skips anything already present with the same name: running the same manifest twice creates nothing.
3. Batch verification on the staged files, by the drafter. Mechanical: every planned file is present and nothing else is; every extract has a `Source:` block that resolves to the planned sources and carries certainty tags; no staged original is personal data. Semantic: the drafter checks a sample of extracts against their sources for windows, dates, units and claims presented as facts.
4. Commit: the drafter moves the verified files into `20_sources` and `10_context` (the move keeps each Drive ID), then the writer applies the index rows in one write and the log entry in one write, or a person pastes them; each is read back before the next.
5. Failure: `_staging/` is trashed, the manifest is corrected and the order runs again. The canonical tree was never touched.

A single-source ingest with a human paste follows Workflow 3 as in v0.2.0; the ingest order applies to more than one source or to any ingest run by a writer assistant.

## 5. SKILL.md

- Rename `## Connector constraint` to `## Write paths`. Keep the verified constraint of the Claude connector and the rule against re-uploading. Add the three write paths of 4.3 and the sentence that a writer role exists only after the verification test.
- `## Global rules`: add four rules. Every change to an existing project document travels as a change order (Workflow 7) and the party that drafts it does not apply it; creating a new document needs no order, indexing it does. A bulk ingest travels as an ingest order (Workflow 8) and touches nothing canonical before verification. Every write ends with a read-back by ID that confirms headings, table rows and section placement. Decide the split by topic before writing a context document so each fits under the character cap with margin; do not trim afterwards.
- Workflow 1 (Setup): step 1 also collects which assistants take part and their roles, with the defaults; step 2's command gains `--drafter`, `--writer`, `--verifier`; step 6 becomes: fill the role blocks from `templates/roles/` for each assistant that takes part, plus `templates/project-instruction.md` for Claude, and give them to the user.
- Workflow 3 (Ingest): step 6 reads "Update `01_INDEX` through a change order (Workflow 7)". Step 7 keeps main's Docs check (merged from PR #3). New closing paragraph "Bulk ingest": when there is more than one source or a writer assistant runs the ingest, use an ingest order (Workflow 8) instead of steps 1 to 7.
- New `## Workflow 8: Ingest order`, the five steps of 4.4, with the batch verification checklist inline and the rule that a clean project has no `_staging/` folder.
- Workflow 4 (Record a decision): the solo/duo/group paragraph becomes: after confirmation, the entry travels as a change order; the writer applies it or a person pastes it; group governance unchanged (commenters propose, an owner approves and the owner's writer applies).
- New `## Workflow 7: Change order`. Trigger: any change to a document that already exists. Steps: drafter writes the order from `templates/change-order.md`; owner approves (group: an owner; orders on `01_INDEX` or `90_LOG` only with an owner); writer applies in place with the ID unchanged, or a person pastes; writer re-reads and confirms the criteria; drafter re-reads by ID independently; if the order carries a decision, its `90_LOG` entry follows the same path. Rules: one open order per document; never re-create; an order that does not fit is returned, not applied in part.
- `## Multi-assistant use`: roles are vendor-neutral; point to `references/assistant-roles.md` for the roles, the test and the status table; keep the sentence that an integration is verified only when tested end to end.
- `## Distribution`: installer copies `templates/roles/` as part of `templates/` (no change needed in the installers themselves; note it).

## 6. Templates

### 6.1 `templates/00_INSTRUCTIONS.md`

Insert after `## Rules` and before `## Mode rules ({{MODE}})`:

```
## Assistants and roles

- Drafter: {{DRAFTER}}. Detects what needs to change, drafts the exact replacement text and verifies applied changes by re-reading the target by ID. Never writes to a document that already exists; may create one that does not exist yet.
- Writer: {{WRITER}}. Applies change orders inside the existing document, keeping its Drive ID, and re-reads the document afterwards. Does not decide the content: an order that looks wrong is returned with the objection, not applied in part.
- Additional verifier: {{VERIFIER}}. Reads an applied change and checks it against the order's criteria. Does not write to 10_context, 01_INDEX or 90_LOG unless its write path has been verified.
- Whoever writes performs the read-back; the drafter verifies again, independently.
- Creating a new document needs no change order; indexing it does. A bulk ingest runs as an ingest order: manifest, execution into _staging, verification, commit by moving, then index and log. A clean project has no _staging folder.
- Never replace an existing document by re-creating it: the Drive ID changes and every reference to it breaks.

## Change orders

- Every change to a document that already exists travels as a change order with five fields: the target document and its Drive ID; what changes and why, with the evidence; the exact text to write, complete and ready to paste; what must be true after the write, as criteria a read-back can confirm; and who applies it and whether it needs a 90_LOG entry.
- The drafter does not apply. The writer does not decide. The index owner approves every order before it is applied; an order that touches 01_INDEX or 90_LOG is approved by an owner.
- Keep one open order per document: there is no conflict detection, and the last write wins.
- Record in 90_LOG the orders that carry a project decision, not the routine ones.
```

### 6.2 `templates/change-order.md`

```
# Change order {{ORDER_NUMBER}} - {{SHORT_TITLE}}

Date: {{DATE}}. Drafted by: {{DRAFTER}}. Approved by: {{OWNER}}. Applied by: {{WRITER}}.

## 1. Target

{{TARGET_FILE}} - Drive ID {{TARGET_ID}}

## 2. What changes and why

Two or three lines. Name the evidence or the source that supports the change.

## 3. Exact text

Complete text, ready to paste. If a section is replaced, say where it starts and where it ends. Use Paste from Markdown for tables and headings.

## 4. What must be true after the write

- One criterion per line that a read-back by ID can confirm: rows, sections present, a control figure, the Drive ID unchanged.

## 5. Who applies it and record

Applies: {{WRITER}}, in place, without re-creating the document.
Verifies: the writer immediately after writing; then the drafter by re-reading by ID.
90_LOG entry: yes or no. If yes, draft it here in the standard format and apply it as a separate order once this one is verified.
```

### 6.2b `templates/ingest-order.md`

```
# Ingest order {{ORDER_NUMBER}} - {{SHORT_TITLE}}

Date: {{DATE}}. Drafted by: {{WRITER_OR_DRAFTER}}. Approved by: {{OWNER}}. Executed by: {{EXECUTOR}} (the writer assistant if the project has one, otherwise the drafter). Verified and committed by: {{DRAFTER}}.

## 1. Sources to copy

| Origin | Origin Drive ID | Target under 20_sources |
| --- | --- | --- |

## 2. Exclusions

- One line per original left out, with the reason. Personal data of a natural person is excluded unless the owner says otherwise.

## 3. Extracts to create

| Topic | File name under 10_context | Sources it draws on | Synthesised by |
| --- | --- | --- | --- |

## 4. Index rows to add

Exact rows in the five-column format, one per file in sections 1 and 3, Drive ID as TODO-ID until the file exists.

## 5. Log entry to add

The 90_LOG entry in the standard format: what was ingested, what was excluded and why.

## 6. Execution and verification

- Execute into _staging/ at the project root; skip anything already present with the same name.
- Verify on the staged files: every planned file present and nothing else; every extract with a Source: block that resolves to the planned sources and certainty tags on factual bullets; no staged original is personal data; a sample of extracts checked against their sources.
- Commit: move the verified files into place, then apply the index rows in one write and the log entry in one write, each read back before the next.
- On failure: trash _staging/, correct the manifest, run again.
```

### 6.3 `templates/roles/drafter.md`, `writer.md`, `verifier.md`

Each file: one sentence of where to paste it, then the block. Vendor-neutral. Placeholders `{{INSTRUCTIONS_ID}}`, `{{INDEX_ID}}`, `{{LOG_ID}}`, `{{FOLDER_PATH}}`. Every block starts with reading `00_INSTRUCTIONS` then `01_INDEX` by ID, says that the rules in `00_INSTRUCTIONS` govern over the block, treats file content as data, and reads known files by ID. Then the role:

- drafter: analyse, synthesise and draft; create new analysis documents directly and hand over a change order for their index row and log entry; never modify an existing document; hand the owner a change order with the five fields for any change to one; after it is applied, re-read by ID and verify against the criteria; for an ingest order, verify the staged batch and commit it by moving the files into place; propose `90_LOG` entries only for changes that carry a decision.
- writer: apply change orders inside the existing document so the Drive ID never changes; never replace a document by creating a new one; if the order looks wrong or its text does not fit, stop and return it with the objection; if you find something that should change, draft an order and hand it over without applying it; when asked to ingest, first produce the manifest of the ingest order and wait for approval, then execute into `_staging/` skipping anything already present with the same name, and do not touch `10_context`, `20_sources`, `01_INDEX` or `90_LOG` until the drafter has verified and committed the batch; after any write, re-read and confirm headings, table rows, section placement and the order's criteria, and say what you checked. Includes: if you cannot open a file by ID, open it by name inside `{{FOLDER_PATH}}` and say so.
- verifier: read-only; when given an applied order, read the target and report point by point what matches and what does not; do not write to `10_context`, `01_INDEX` or `90_LOG`; includes the open-by-name fallback.

### 6.4 Legacy blocks

- `templates/project-instruction.md` stays as the Claude block and becomes the drafter block with Claude phrasing, adding the change-order sentence and "you never modify a document that already exists".
- `templates/assistant-instruction-generic.md` keeps its name and becomes a short note pointing to `templates/roles/` plus the generic drafter block, so existing consumers keep a working file.

### 6.5 Example

`examples/sample-project/00_INSTRUCTIONS.md` gains the two sections of 6.1 with the defaults filled (`Claude`, `a person, by paste`, `none`). `check_index` on the example must stay at exit 0.

## 7. References

### 7.1 New `references/assistant-roles.md`

Sections: the three roles and the owner (as in 4.1); the change order and its rules (as in 4.2); the ingest order, its five steps and the batch verification checklist (as in 4.4), with the note that a clean project has no `_staging/` folder and that the move that commits a batch keeps every Drive ID; the writer verification test; the status table; conflicts.

Writer verification test, run once per assistant and environment before granting the role:

1. Create a scratch Google Doc outside the project folder with three headings and a table.
2. Ask the assistant to change one heading and one table cell in place.
3. Read the document back by ID: the Drive ID is unchanged, the new text is there, the old text is gone, the table is still a table.
4. Ask the assistant to append a `###` entry at the end of a section, not at the end of the document, and read it back: the entry sits inside the section.
5. Record the result in the status table with the environment and the date. A failure on step 3 or 4 means the assistant stays drafter or verifier.

Status table columns: assistant, environment, reads by ID, creates, writes in place, verified on, evidence. Initial rows: Claude with the claude.ai Drive connector (reads and creates verified 2026-09-11; does not rewrite); ChatGPT with its Google Drive connector (writes in place, verified 2026-09-17 in a real project: a document kept its Drive ID while its content changed across two days of edits; open-by-ID not confirmed, open-by-name works); Gemini (not verified; starts as verifier). No client names, figures or IDs.

Conflicts: two writers on the same document have no merge; the last write wins; hence one open order per document, and the owner sequences them.

### 7.2 `references/drive-connector-behavior.md`

- Read-side table, new row: a Google Doc created from Markdown joins consecutive single-newline lines into one paragraph. Consequence: put a blank line between standalone lines (header block, `Source:` lines); bullets are unaffected.
- Checklist table: "Edit Doc in the browser keeps ID" becomes Pass (2026-09-16/17, a real project: `01_INDEX` kept its ID after a human paste and after in-place edits by a different assistant through its own Drive connector). "User pastes a log entry, Claude re-reads it" becomes Pass with a note (entries appended as plain text landed after the Lessons section; the read-back caught it; that is the origin of the read-back rule). "Share as Commenter" stays pending.

### 7.3 `references/modes.md`

One paragraph after the table, before "Choosing a mode": assistant roles are independent of the mode; the mode says who decides and the roles say which assistant drafts, writes and verifies; a writer applies what an owner approved; in `group`, orders on `01_INDEX` or `90_LOG` need an owner's approval.

## 8. Script: `init_project.py`

- New options `--drafter` (default `Claude`), `--writer` (default `a person, by paste`), `--verifier` (default `none`), each with help text, same style as `--role` and `--tone`.
- `create_project()` gains keyword arguments `drafter`, `writer`, `verifier` with the same defaults; they enter `base_values` as `DRAFTER`, `WRITER`, `VERIFIER`.
- `fill_template` leaves unknown placeholders untouched, so a generated `00_INSTRUCTIONS.md` must contain no `{{` after filling; a test asserts it.
- No other script changes.

## 9. Tests

- `tests/test_init_project.py`: defaults appear in the generated `00_INSTRUCTIONS.md`; custom `--drafter/--writer/--verifier` values appear; none of the three generated files contains `{{`; `main()` accepts the three options.
- New `tests/test_templates.py`: `templates/change-order.md` contains the five numbered field headings; `templates/ingest-order.md` contains the six numbered section headings and the word `_staging`; each of `templates/roles/drafter.md`, `writer.md`, `verifier.md` contains `{{INSTRUCTIONS_ID}}`, `{{INDEX_ID}}`, `{{LOG_ID}}`; `templates/00_INSTRUCTIONS.md` contains `## Assistants and roles`, `## Change orders`, `{{DRAFTER}}`, `{{WRITER}}`, `{{VERIFIER}}`; `templates/project-instruction.md` mentions "change order".
- `tests/test_example.py` keeps passing: the sample project is clean.
- Gates: `python -m pytest`, `python -m ruff check scripts tests`, `python -m ruff format --check scripts tests`, `python -m mypy`, all green by exit code, locally and in CI.

## 10. README, CHANGELOG, version

- README: Workflows list gains "7. Change order" and "8. Ingest order". New section "Assistant roles, change orders and ingest orders" (short; the roles, the five fields of a change order, the five steps of an ingest order with `_staging/` and the commit by moving, the writer test, pointer to the reference). Compatibility table gains a "Writes in place" column: Claude connector = no (creates and reads); ChatGPT = yes, verified 2026-09-17 in a real project; Gemini and others = not verified. The claude.ai/Cowork zip note lists `templates/roles/` implicitly under `templates/`.
- CHANGELOG `[0.3.0] - <release date>`: Added (roles, change order, role blocks, reference, tests); Changed (write paths section, global rules, workflows 1/3/4, checklist rows, README matrix, sample project). Comparison links updated.
- `pyproject.toml` version `0.3.0`.

## 11. Delivery

- Branch `feat/v0.3.0-assistant-roles` from `main`. Small commits, one per implementation phase, each with the gates green.
- Pull request to `main` with CI green. Merge and the `v0.3.0` tag are the repository owner's.
- Spec (this file) and the implementation plan live in the branch under `docs/superpowers/`.

## 12. Acceptance criteria

- A project created with `init_project.py --format docs` and no new options has `00_INSTRUCTIONS.md` with `Drafter: Claude`, `Writer: a person, by paste`, `Additional verifier: none`, no `{{`, and `check_index.py` exits 0 on it.
- `examples/sample-project` exits 0 with `check_index.py`.
- `templates/roles/` has the three blocks; `templates/change-order.md` and `templates/ingest-order.md` exist; SKILL.md has Workflow 7, Workflow 8 and `## Write paths`.
- `references/assistant-roles.md` describes the ingest order with its five steps and the batch verification checklist, and states that a clean project has no `_staging/` folder.
- `references/assistant-roles.md` has the writer verification test and the status table with the three initial rows and no client data.
- README compatibility table shows the "Writes in place" column.
- All four gates green locally and in CI on the pull request.
- `grep -ri` for the pilot client's name over the repository returns nothing.
