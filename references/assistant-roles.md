# Assistant roles, change orders and ingest orders

Roles are a property of the project, recorded in 00_INSTRUCTIONS, and independent of the human mode. The mode says who decides; the roles say which assistant drafts, which one writes and which one verifies. The defaults reproduce a single-assistant project: drafter Claude, writer a person by paste, no additional verifier.

## Roles

- Drafter. Reads, analyses and synthesises; creates new analysis documents directly; detects what must change in existing documents and writes the change order with the exact replacement text. Never writes to a document that already exists. Verifies applied changes and ingest batches independently by re-reading by ID, and commits a verified ingest batch by moving its files into place.
- Writer. Applies a change order inside the existing document, keeping its Drive ID, and re-reads the document afterwards. Does not decide the content: if the order looks wrong or does not fit, returns it with the objection instead of applying part of it. If it notices something that should change, drafts a change order and hands it over without applying it. In Docs format with no assistant writer, the writer is a person who pastes with Paste from Markdown; in md format, whoever edits the local mirror.
- Verifier. Optional. Reads an applied change and checks it point by point against the order's criteria. May leave a new original in 20_sources when asked. Never writes to 10_context, 01_INDEX or 90_LOG while its write path is unverified.
- Owner. The human index owner from the mode. Approves every change order and every ingest order before it is applied. In group mode, orders that touch 01_INDEX or 90_LOG need an owner.

Why the drafter and the writer are never the same party: a drafting error is caught before it is recorded, and the party that writes never decides what the document says.

## Change order

The change order is the only way a change to an existing document travels. Five fields, always all five:

1. Target: the document and its Drive ID.
2. What changes and why: two or three lines, with the evidence or the source behind it.
3. Exact text: complete and ready to paste, not a description of it. When a section is replaced, the order names where it starts and ends.
4. What must be true after the write: criteria a read-back can confirm, such as rows, sections present, a control figure, the Drive ID unchanged.
5. Who applies it, and whether it needs a 90_LOG entry.

Rules:

- The drafter does not apply. The writer does not decide.
- The owner approves before anything is applied.
- Two verifications follow every write: the writer's immediate read-back and the drafter's independent one.
- Keep one open order per document. There is no conflict detection between two writers; the last write wins. The owner sequences orders.
- Record in 90_LOG the orders that carry a project decision, not the routine ones.
- Creating a new document needs no order; indexing it does.

Template: templates/change-order.md.

## Ingest order

A bulk ingest is the most expensive thing to undo, so it runs so that nothing canonical is touched until it is verified. It applies to more than one source, or to any ingest run by a writer assistant. A single-source ingest with a human paste follows Workflow 3 as before.

1. Manifest, with no writes: sources to copy with origin and Drive ID and target subfolder under 20_sources; exclusions with the reason, where an original that is personal data of a natural person is excluded unless the owner says otherwise; extracts to create with topic, file name, the sources each draws on and who synthesises it; the exact index rows and the exact 90_LOG entry the batch will add. The owner approves the manifest.
2. Execution into _staging/, a transient folder at the project root. The writer creates copies and extracts there, never in 10_context or 20_sources. Before copying, it lists the target and skips anything already present with the same name: running the same manifest twice creates nothing.
3. Batch verification on the staged files, by the drafter. Mechanical: every planned file is present and nothing else is; every extract has a Source: block that resolves to the planned sources and carries certainty tags on its factual bullets; no staged original is personal data. Semantic: the drafter checks a sample of extracts against their sources for time windows, dates, units and claims presented as facts.
4. Commit: the drafter moves the verified files into 20_sources and 10_context, which keeps each Drive ID; then the writer applies the index rows in one write and the log entry in one write, or a person pastes them; each is read back before the next.
5. Failure: _staging/ is trashed, the manifest is corrected and the order runs again. The canonical tree was never touched.

A clean project has no _staging/ folder. The scripts scan only 10_context and 20_sources, so a leftover _staging/ is found by listing the project folder, not by check_index.

Template: templates/ingest-order.md.

## Writer verification test

Run once per assistant and environment before granting the writer role. Nothing here touches a real project.

1. Create a scratch Google Doc outside any project folder with three headings and a table.
2. Ask the assistant to change one heading and one table cell in place.
3. Read the document back by ID: the Drive ID is unchanged, the new text is there, the old text is gone, and the table is still a table.
4. Ask the assistant to append a level-3 entry at the end of one section, not at the end of the document, and read it back: the entry sits inside that section.
5. Record the result in the table below with the environment and the date. A failure on step 3 or 4 means the assistant stays drafter or verifier.

## Status by assistant

| Assistant | Environment | Reads by ID | Creates | Writes in place | Verified on | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Claude | claude.ai Drive connector, also from Claude Code desktop | yes | yes | no; update only renames and moves | 2026-09-11 | Connector tool schemas and a live test: create, read and rename verified; no content update operation exists. |
| ChatGPT | its Google Drive connector | not confirmed; opens by name inside the folder | yes | yes | 2026-09-17 | In a real project, 01_INDEX kept its Drive ID while its content changed across two days of the assistant's edits; a re-created document would have carried a new ID. |
| Gemini | Google Workspace | not tested | not tested | not tested | pending | Starts as verifier until it passes the test. |

Protocol compatibility and a verified write path are separate claims. An assistant that reads the folder can hold the drafter or verifier role without any test; the writer role needs the test above.

## Conflicts

Two writers on the same document have no merge: the last write wins. Hence one open order per document, one open ingest order at a time, and the owner sequencing them.
