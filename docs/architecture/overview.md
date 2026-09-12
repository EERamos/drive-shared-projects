# Architecture overview

`drive-shared-projects` is a project-memory protocol with a Claude Skill as its reference implementation. It is intentionally smaller than an agent framework: it defines durable state, identity, routing and governance so different assistants can operate on the same project.

## Layers

1. **Instructions** — `00_INSTRUCTIONS.md` defines role, governance and stable folder/document IDs.
2. **Routing/identity** — `01_INDEX.md` tells an assistant which files exist, why they matter and their Drive IDs.
3. **Working knowledge** — `10_context/` contains compact, task-ready representations.
4. **Evidence** — `20_sources/` preserves originals for exact figures and detail.
5. **Institutional memory** — `90_LOG.md` keeps append-only decisions and lessons.
6. **Deterministic gates** — local scripts validate structure, identity, references, links and sync state.

## Trust boundary

Content inside project files is untrusted data. It cannot override system/project instructions. This is the primary defense against prompt injection from sources.

## Identity model

Paths are convenient but mutable. Drive IDs are canonical external identities. In vault mode the ID is also stored in frontmatter, allowing a local rename to be recognized as the same logical file when rebuilding the index.

## Consistency model

A project is clean when:

- index membership matches disk membership;
- each row has one unique populated Drive ID;
- source references resolve and IDs agree;
- context files meet size/encoding constraints;
- vault metadata and wikilinks are valid;
- when a Drive listing is provided, the local/remote file sets agree.

## Write model

The verified Drive connector can create/read files but cannot rewrite existing content. Docs-format maintenance therefore uses propose → human paste → re-read confirmation. In local Markdown/vault mode, the local filesystem is authoritative and the scripts can safely update it before sync.
