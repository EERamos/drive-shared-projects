"""Create a local drive-shared-projects folder tree from the templates.

Usage:
    python scripts/init_project.py --name "My Project" --mode duo --format docs --out ./my-project

Exit codes: 0 created, 1 refused (target not empty), 2 usage error.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from collections.abc import Sequence
from pathlib import Path

from common import (
    CONTEXT_DIR,
    INDEX_FILE,
    INSTRUCTIONS_FILE,
    LOG_FILE,
    SOURCES_DIR,
    TEMPLATES_DIR,
    Format,
    Mode,
    fill_template,
    read_text,
    write_text,
)

EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_USAGE = 2

_TOP_LEVEL_FILES = (INSTRUCTIONS_FILE, INDEX_FILE, LOG_FILE)
_SUBDIRS = (CONTEXT_DIR, SOURCES_DIR)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a shared-project folder tree.")
    parser.add_argument("--name", required=True, help="Project name shown in the documents.")
    parser.add_argument("--mode", required=True, choices=[m.value for m in Mode])
    parser.add_argument("--format", required=True, choices=[f.value for f in Format])
    parser.add_argument("--out", required=True, type=Path, help="Target directory.")
    parser.add_argument("--owner", default="unassigned", help="Index owner name.")
    return parser


def create_project(
    out: Path,
    name: str,
    mode: Mode,
    fmt: Format,
    owner: str,
    today: dt.date,
    templates: Path = TEMPLATES_DIR,
) -> None:
    """Write the folder tree into `out`. Raise FileExistsError if `out` is not empty."""
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"{out} exists and is not empty")
    base_values = {
        "NAME": name,
        "MODE": mode.value,
        "FORMAT": fmt.value,
        "DATE": today.isoformat(),
        "OWNER": owner,
    }
    fragment = read_text(templates / "modes" / f"{mode.value}.md").rstrip("\n")
    values = {**base_values, "MODE_RULES": fill_template(fragment, base_values)}

    out.mkdir(parents=True, exist_ok=True)
    for fname in _TOP_LEVEL_FILES:
        write_text(out / fname, fill_template(read_text(templates / fname), values))
    for sub in _SUBDIRS:
        (out / sub).mkdir()
        write_text(out / sub / ".gitkeep", "")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return EXIT_USAGE if exc.code else EXIT_OK
    try:
        create_project(
            out=args.out,
            name=args.name,
            mode=Mode(args.mode),
            fmt=Format(args.format),
            owner=args.owner,
            today=dt.date.today(),
        )
    except FileExistsError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    print(f"created {args.out}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
