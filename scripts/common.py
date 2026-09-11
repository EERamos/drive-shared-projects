"""Shared constants and helpers for the drive-shared-projects scripts."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

INSTRUCTIONS_FILE = "00_INSTRUCTIONS.md"
INDEX_FILE = "01_INDEX.md"
LOG_FILE = "90_LOG.md"
CONTEXT_DIR = "10_context"
SOURCES_DIR = "20_sources"
ID_PLACEHOLDER = "TODO-ID"
DEFAULT_MAX_CHARS = 50_000
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

INDEX_HEADER = "| File | Drive ID | What it contains | When to read | Owner |"
INDEX_SEPARATOR = "| --- | --- | --- | --- | --- |"
INDEX_COLUMNS = 5

_CELL_SPLIT = re.compile(r"(?<!\\)\|")
_HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)
_LEADING_PREFIX = re.compile(r"^[\d_\-\s]+")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_PLACEHOLDER = re.compile(r"\{\{([A-Z_]+)\}\}")


class Mode(Enum):
    """Who edits the project and how decisions are governed."""

    SOLO = "solo"
    DUO = "duo"
    GROUP = "group"


class Format(Enum):
    """Storage format of the living documents in Drive."""

    DOCS = "docs"
    MD = "md"


@dataclass(frozen=True)
class IndexRow:
    """One row of the 01_INDEX table."""

    file: str
    drive_id: str
    summary: str
    when_to_read: str
    owner: str

    def to_markdown(self) -> str:
        cells = (self.file, self.drive_id, self.summary, self.when_to_read, self.owner)
        return "| " + " | ".join(_escape_cell(c) for c in cells) + " |"


def _escape_cell(cell: str) -> str:
    return cell.replace("|", "\\|").strip()


def _unescape_cell(cell: str) -> str:
    return cell.strip().replace("\\|", "|")


def _is_separator(cell: str) -> bool:
    return cell != "" and set(cell) <= {"-", ":"}


def parse_index(text: str) -> list[IndexRow]:
    """Return the data rows of the first five-column Markdown table in `text`."""
    rows: list[IndexRow] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = [_unescape_cell(c) for c in _CELL_SPLIT.split(stripped)[1:-1]]
        if len(cells) != INDEX_COLUMNS:
            continue
        if cells[0] == "File" or _is_separator(cells[0]):
            continue
        rows.append(IndexRow(*cells))
    return rows


def render_index_table(rows: Iterable[IndexRow]) -> str:
    """Render header, separator and rows as a Markdown table ending with a newline."""
    lines = [INDEX_HEADER, INDEX_SEPARATOR, *(r.to_markdown() for r in rows)]
    return "\n".join(lines) + "\n"


def replace_index_table(text: str, new_table: str) -> str:
    """Replace the first contiguous block of table lines in `text` with `new_table`.

    If `text` has no table, append `new_table` after a blank line.
    """
    lines = text.splitlines(keepends=True)
    start = next((i for i, ln in enumerate(lines) if ln.lstrip().startswith("|")), None)
    if start is None:
        sep = "" if text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
        return text + sep + new_table
    end = start
    while end < len(lines) and lines[end].lstrip().startswith("|"):
        end += 1
    return "".join(lines[:start]) + new_table + "".join(lines[end:])


def first_heading(text: str) -> str | None:
    """Return the text of the first Markdown heading, or None."""
    match = _HEADING.search(text)
    return match.group(1) if match else None


def normalize_stem(path: str) -> str:
    """Lower-case file stem without numeric prefix, punctuation collapsed to '-'."""
    stem = Path(path).stem.lower()
    stem = _LEADING_PREFIX.sub("", stem)
    return _NON_ALNUM.sub("-", stem).strip("-")


def fill_template(text: str, values: Mapping[str, str]) -> str:
    """Replace `{{KEY}}` placeholders present in `values`; leave unknown ones untouched."""

    def _sub(match: re.Match[str]) -> str:
        key = match.group(1)
        return values[key] if key in values else match.group(0)

    return _PLACEHOLDER.sub(_sub, text)


def relative_posix(root: Path, path: Path) -> str:
    """Path of `path` relative to `root` with forward slashes."""
    return path.relative_to(root).as_posix()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")
