# Connector samples

Tool results of the claude.ai Google Drive connector, captured on 2026-09-13 from Claude Code
desktop against a throwaway project created with the v0.2.0 templates. Every Drive ID and the
owner address were replaced with fictional values of the same shape; the escaping rules observed
in the originals were applied to the replacements (an underscore in Doc prose reads back as
`\_`, inside a Doc table cell as `\\\_`).

| File | Origin |
| --- | --- |
| `00_INSTRUCTIONS.json` | `read_file_content` of the instructions Doc |
| `01_INDEX.json` | `read_file_content` of the index Doc right after creation, two rows with `TODO-ID` |
| `01_INDEX_clean.json` | the same Doc after the owner filled the IDs and added a row, derived by applying the observed cell escaping |
| `momentum_extract.json` | a `10_context` extract Doc; shows the `Source:` and `Extracted:` lines joined into one |
| `pricing_notes.md.json` | a plain `.md` kept without conversion |
| `zz_format_probe.json` | a Doc with the awkward cases: bold, code, literal pipe, nested list, code fence, blockquote |
| `10_context.json`, `20_sources.json`, `project.json` | `search_files` with `parentId` on the three folders |
