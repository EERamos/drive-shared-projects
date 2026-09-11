# drive-shared-projects

A Claude skill that turns a Google Drive folder into the equivalent of a shared Claude project: common instructions, a shared knowledge base in Markdown, and an append-only decision log. Works with Pro and Max accounts through the Google Drive connector; no Team plan needed.

## What you get

- A fixed folder layout: 00_INSTRUCTIONS, 01_INDEX, 10_context/, 20_sources/, 90_LOG.
- Templates for every document and a ready-to-paste project instruction block.
- Three modes (solo, duo, group) with governance rules that the skill applies at setup.
- Optional scripts for Claude Code: create the tree, refresh the index, validate the folder with an exit code.

## Works with any assistant

The folder is plain Drive content: Google Docs written in Markdown, .md files and your sources. Nothing in it is specific to Claude. Any assistant that can read your Drive can be pointed at the same folder with the same instruction block. That covers ChatGPT, Gemini, Grok, Copilot and a local model behind a Drive tool. A team can therefore mix assistants and still share one knowledge base and one decision log. Use `templates/assistant-instruction-generic.md` for assistants other than Claude. The skill itself (the setup, ingest and maintenance workflows) runs in Claude, and the other assistants consume what it maintains.

## Install

### Claude Code

Clone the repo and run the installer; it copies SKILL.md, templates, references and scripts into `~/.claude/skills/drive-shared-projects`.

Windows (PowerShell):

```powershell
git clone https://github.com/EERamos/drive-shared-projects.git
cd drive-shared-projects
.\install.ps1
```

If PowerShell refuses to run the script because of the execution policy, run it as a file instead:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

macOS / Linux:

```bash
git clone https://github.com/EERamos/drive-shared-projects.git
cd drive-shared-projects
./install.sh
```

Without git, use the green Code button on GitHub, choose Download ZIP, unzip it, and run the installer from the unzipped folder.

The installers copy over what is already installed; they do not remove files that a later version deleted. To upgrade, delete `~/.claude/skills/drive-shared-projects` first and install again.

### claude.ai and Cowork

Upload a zip that contains only what these environments use. Make a new folder named `drive-shared-projects` somewhere outside the clone and copy three things into it: `SKILL.md`, `templates/` and `references/`. That keeps `.git`, `docs/`, `tests/`, `examples/` and `scripts/` out of the archive. Then zip that folder, so the archive contains `drive-shared-projects/SKILL.md` and not a loose `SKILL.md`, and upload it under Settings, Skills. On Windows: right click the folder, Send to, Compressed (zipped) folder. On macOS: right click the folder, Compress. Keep the folder named `drive-shared-projects`; it has to match the `name` in the SKILL.md frontmatter. Scripts are not used there; the skill falls back to doing everything through the connector.

Every member of a shared project installs the skill on their own account and needs the Google Drive connector enabled.

## Set up a project in ten minutes

0. Connect Google Drive. On claude.ai: Settings, Connectors, Google Drive, and authorize the account that holds the folder. The connector has to be enabled in Claude Code and in Cowork too; nothing in this skill works without it.
1. Open a chat and say "set up a shared project on Drive". The skill asks for the name, the mode, the format and who owns the index.
2. It creates the folder, the subfolders and the three documents in your Drive and hands you an instruction block with the real file IDs.
3. Create a Claude project (or a Cowork task) and paste the block into its instructions.
4. Share the Drive folder following the mode's sharing rule. Every member pastes the same block into their own project.
5. Drop the first source into 20_sources and ask Claude to ingest it. From then on every chat starts by reading the instructions and the index.

Claude creates the folders and every new document, but the Drive connector cannot rewrite a file that already exists, so index rows and log entries come back to you as text to paste (Claude then re-reads the file to confirm). In Claude Code with a local mirror the skill can apply those changes for you: see the Scripts section below for that path.

## Scripts (Claude Code only)

All scripts are standard library, Python 3.10 or newer. They run against a local copy of the project folder and never touch Drive. The skill calls them from where the installer put them, `~/.claude/skills/drive-shared-projects`, because the working directory is your own project rather than this repository.

Create the tree:

```bash
python ~/.claude/skills/drive-shared-projects/scripts/init_project.py --name "Quant Research" --mode duo --format docs --owner "Ana" --out ./quant-research
```

Check it. This is the deterministic gate for the maintenance workflow: `check_index.py` returns 0 when the index and the folder agree, 1 with a list of findings, 2 on a usage error.

```bash
python ~/.claude/skills/drive-shared-projects/scripts/check_index.py --root ./quant-research
```

Refresh the index. Always print first and read what comes out:

```bash
python ~/.claude/skills/drive-shared-projects/scripts/build_index.py --root ./quant-research
```

That prints the table it would write, keeping the Drive IDs, summaries and owners already in the index. Compare it with the current table before going further, because rows for files that no longer exist are dropped. Once the printed table is what you want, write it:

```bash
python ~/.claude/skills/drive-shared-projects/scripts/build_index.py --root ./quant-research --write
```

`--write` lists the rows it removed on stderr, but by then the file is already rewritten, which is why the print step comes first.

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
