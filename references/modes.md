# Modes

The skill asks for the mode during setup and records it in 00_INSTRUCTIONS. The folder layout never changes with the mode; only these rules do.

| Rule | solo | duo | group (five or more) |
| --- | --- | --- | --- |
| Index owner | the person | one named owner; the other proposes rows | one named owner; others propose rows through log entries |
| Author field in log entries | optional | required | required |
| Drive sharing | none | both Editor | owners Editor, everyone else Commenter |
| Changing 00_INSTRUCTIONS | direct | direct, then a log entry | log entry with approval first, then edit |
| Claude confirms before writing | always | always | always |

## Choosing a mode

- solo: one person, one Claude account. Fastest. Use it for personal projects or while prototyping the folder before inviting others.
- duo: two people who both edit. One of them owns the index so it never drifts. Use it for a two-person collaboration.
- group: five or more people, or any group where most members only read. Only owners edit; everyone else comments and proposes through the log.

Three or four people: pick duo if everyone edits, group if most only read.

## Changing the mode later

Add a log entry that states the new mode and the new index owner, then edit the "Mode rules" section of 00_INSTRUCTIONS to the fragment for the new mode (see templates/modes/). In Claude Code, re-running init_project.py into an empty folder and copying the new "Mode rules" section is the quickest way.
