# drive-shared-projects

A Claude skill that turns a Google Drive folder into the equivalent of a shared Claude project: common instructions, a shared knowledge base in Markdown, and an append-only decision log. Works with Pro and Max accounts through the Google Drive connector; no Team plan needed.

## What you get

- A fixed folder layout: 00_INSTRUCTIONS, 01_INDEX, 10_context/, 20_sources/, 90_LOG.
- Templates for every document and a ready-to-paste project instruction block.
- Three modes (solo, duo, group) with governance rules that the skill applies at setup.
- Optional scripts for Claude Code: create the tree, refresh the index, validate the folder with an exit code.

## Works with any assistant

The folder is plain Drive content: Google Docs written in Markdown, .md files and your originals. Nothing in it is specific to Claude. Any assistant that can read your Drive (ChatGPT, Gemini, Grok, Copilot, a local model behind a Drive tool) can be pointed at the same folder with the same instruction block, so a team can mix assistants and still share one knowledge base and one decision log. Use `templates/assistant-instruction-generic.md` for assistants other than Claude; the skill itself (the setup, ingest and maintenance workflows) runs in Claude, and the other assistants consume what it maintains.

## Install

### Claude Code

Clone the repo and run the installer; it copies SKILL.md, templates, references and scripts into `~/.claude/skills/drive-shared-projects`.

```powershell
git clone https://github.com/EERamos/drive-shared-projects.git
cd drive-shared-projects
.\install.ps1
```

```bash
git clone https://github.com/EERamos/drive-shared-projects.git
cd drive-shared-projects
./install.sh
```

### claude.ai and Cowork

Zip `SKILL.md`, `templates/` and `references/` into `drive-shared-projects.zip` and upload it under Settings, Skills. Scripts are not used there; the skill falls back to doing everything through the connector.

Every member of a shared project installs the skill on their own account and needs the Google Drive connector enabled.

## Set up a project in ten minutes

1. Open a chat and say "set up a shared project on Drive". The skill asks for the name, the mode and the format.
2. It creates the folder, the subfolders and the three documents in your Drive and hands you an instruction block with the real file IDs.
3. Create a Claude project (or a Cowork task) and paste the block into its instructions.
4. Share the Drive folder following the mode's sharing rule. Every member pastes the same block into their own project.
5. Drop the first original into 20_sources and ask Claude to ingest it. From then on every chat starts by reading the instructions and the index.

## Scripts (Claude Code only)

All scripts are standard library, Python 3.10 or newer.

```bash
python scripts/init_project.py --name "Quant Research" --mode duo --format docs --owner "Ana" --out ./quant-research
python scripts/build_index.py --root ./quant-research --write
python scripts/check_index.py --root ./quant-research
```

`check_index.py` returns 0 when the index and the folder agree, 1 with a list of findings, 2 on a usage error. It is the deterministic gate for the maintenance workflow.

## Repository layout

| Path | Purpose |
| --- | --- |
| SKILL.md | the skill: workflows and rules |
| templates/ | documents Claude fills; modes/ holds the per-mode rule fragments; assistant-instruction-generic.md is the vendor-neutral instruction block |
| references/ | verified connector behavior and mode governance |
| scripts/ | init_project, build_index, check_index |
| tests/ | pytest suite for the scripts |
| examples/sample-project/ | a filled example that passes check_index |
| docs/superpowers/ | design spec and implementation plan |

## Development

```bash
python -m pip install "pytest>=8" "hypothesis>=6" "ruff>=0.5" "mypy>=1.10"
python -m pytest
python -m ruff check scripts tests
python -m ruff format --check scripts tests
python -m mypy
```

## Versioning

Semantic versions, tagged on the repository. Consumers pin a tag. Changes are listed in CHANGELOG.md.

## License

MIT.
