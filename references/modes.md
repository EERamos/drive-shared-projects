# Modes

The skill asks for the mode during setup and records it in 00_INSTRUCTIONS. The folder layout never changes with the mode; only the governance rules do.

| Rule | solo | duo | group (five or more) |
| --- | --- | --- | --- |
| Index owner | the person | one named owner; the other proposes rows | one named owner; others propose rows through comments/chat |
| Author field in log entries | optional | required | required |
| Drive sharing | none | both Editor | owners Editor, everyone else Commenter |
| Index proposal path | direct | non-owner proposes to owner | member proposes; owner records approval in 90_LOG and updates index |
| Changing 00_INSTRUCTIONS | direct | direct, then a log entry | approval first; owner records the decision, then edits |
| Assistant confirms before writing | always | always | always |

## Choosing a mode

- solo: one person. Fastest for personal projects and prototypes.
- duo: two people who both edit. One owns the index so it never drifts.
- group: five or more people, or any group where most members only read/comment. Only owners edit the canonical files.

Three or four people: pick duo if everyone edits, group if most only read.

## Why commenters do not write the log themselves

A Drive Commenter cannot edit 90_LOG. In group mode the proposal therefore happens through a Drive comment or collaboration chat. The owner approves it, appends the approved proposal/decision to 90_LOG, and then updates 01_INDEX. This keeps permissions and governance consistent.

## Changing the mode later

Add a log entry that states the new mode and index owner, then edit the Mode rules section of 00_INSTRUCTIONS to the fragment for the new mode. In Claude Code, generate a temporary empty project with `init_project.py` and copy only the new mode fragment if useful.
