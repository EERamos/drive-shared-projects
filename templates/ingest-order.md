Copy this file for a bulk ingest: more than one source, or any ingest run by a writer assistant. Nothing is written until the owner approves sections 1 to 5.

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
- Commit: the drafter moves the verified files into place; then the writer applies the index rows in one write and the log entry in one write, or a person pastes them; each is read back before the next.
- On failure: trash _staging/, correct the manifest, run again.
