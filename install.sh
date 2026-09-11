#!/usr/bin/env bash
# Copies the skill into the user's Claude Code skills folder.
# Usage: ./install.sh [destination-folder]
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
dest="${1:-$HOME/.claude/skills/drive-shared-projects}"
mkdir -p "$dest"
for item in SKILL.md templates references scripts; do
  cp -R "$here/$item" "$dest/"
done
echo "Installed drive-shared-projects to $dest"
