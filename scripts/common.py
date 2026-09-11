"""Shared constants and helpers for the drive-shared-projects scripts."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
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
_HEADING = re.compile(r"^#{1,6}[ \t]+(.+?)\s*$", re.MULTILINE)
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


def _split_lines(text: str) -> list[str]:
    """Split `text` on newlines only, keeping the newline on every line but the last.

    Unlike `str.splitlines` this ignores exotic line boundaries such as form feed,
    so a table cell that contains one stays inside its row. `"".join` restores `text`.
    """
    parts = text.split("\n")
    lines = [part + "\n" for part in parts[:-1]]
    if parts[-1] != "":
        lines.append(parts[-1])
    return lines


def _is_table_line(line: str) -> bool:
    return line.lstrip().startswith("|")


def _row_cells(line: str) -> list[str] | None:
    """Split one table line into unescaped cells, or None if it is not a table row."""
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    return [_unescape_cell(c) for c in _CELL_SPLIT.split(stripped)[1:-1]]


def _index_table_span(lines: Sequence[str]) -> tuple[int, int] | None:
    """Return the [start, end) range of the first table block that holds index rows.

    A table block is a contiguous run of lines starting with `|`; it is the index
    when at least one of its rows has exactly `INDEX_COLUMNS` cells.
    """
    position = 0
    while position < len(lines):
        if not _is_table_line(lines[position]):
            position += 1
            continue
        start = position
        while position < len(lines) and _is_table_line(lines[position]):
            position += 1
        parsed = (_row_cells(line) for line in lines[start:position])
        if any(cells is not None and len(cells) == INDEX_COLUMNS for cells in parsed):
            return start, position
    return None


def parse_index(text: str) -> list[IndexRow]:
    """Return the data rows of the first five-column Markdown table in `text`."""
    lines = _split_lines(text)
    span = _index_table_span(lines)
    if span is None:
        return []
    start, end = span
    rows: list[IndexRow] = []
    for line in lines[start:end]:
        cells = _row_cells(line)
        if cells is None or len(cells) != INDEX_COLUMNS:
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
    """Replace the index table block of `text` with `new_table`.

    The block is the one `parse_index` reads, so other tables are left alone.
    If `text` has no index table, append `new_table` after a blank line.
    """
    lines = _split_lines(text)
    span = _index_table_span(lines)
    if span is None:
        sep = "" if text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
        return text + sep + new_table
    start, end = span
    return "".join(lines[:start]) + new_table + "".join(lines[end:])


def first_heading(text: str) -> str | None:
    """Return the text of the first Markdown heading, or None."""
    match = _HEADING.search(text)
    return match.group(1) if match else None


def normalize_stem(path: str) -> str:
    """Lower-case file stem without numeric prefix, punctuation collapsed to '-'.

    Accents are folded, so "Analisis" and its accented spelling give the same stem.
    A stem that is only a numeric prefix, such as "2024", is kept as it is.
    """
    decomposed = unicodedata.normalize("NFKD", Path(path).stem)
    stem = "".join(c for c in decomposed if not unicodedata.combining(c)).lower()
    without_prefix = _LEADING_PREFIX.sub("", stem)
    if without_prefix != "":
        stem = without_prefix
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
    """Read `path` as UTF-8 text."""
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    """Write `text` to `path` as UTF-8 with LF line endings on every platform."""
    path.write_text(text, encoding="utf-8", newline="\n")
