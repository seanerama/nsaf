"""Per-profile append-only history log (see contracts/storage-layout.md)."""

from __future__ import annotations

import re

from .models import HistoryEntry
from .paths import history_path

_UNESCAPED_PIPE = re.compile(r"(?<!\\)\|")

_HEADER = (
    "| date | topic | title | source | url | dedup_key |\n"
    "|------|-------|-------|--------|-----|-----------|\n"
)
_FIELDS = ("date", "topic", "title", "source", "url", "dedup_key")


def _cell(value: str | None) -> str:
    """Sanitize a value for a markdown table cell (no pipes/newlines)."""
    s = "" if value is None else str(value)
    return s.replace("|", "\\|").replace("\n", " ").strip()


def _row(entry: HistoryEntry) -> str:
    return "| " + " | ".join(_cell(getattr(entry, f)) for f in _FIELDS) + " |\n"


def read_history(slug: str) -> list[HistoryEntry]:
    """Parse a profile's history.md into HistoryEntry rows (empty if absent)."""
    path = history_path(slug)
    if not path.exists():
        return []
    entries: list[HistoryEntry] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        parts = _UNESCAPED_PIPE.split(line)[1:-1]  # drop empties from leading/trailing pipe
        cells = [c.strip().replace("\\|", "|") for c in parts]
        if len(cells) != len(_FIELDS):
            continue
        if cells[0].lower() == "date" or set(cells[0]) <= {"-", " "}:
            continue  # header or separator row
        data = dict(zip(_FIELDS, cells, strict=True))
        data["url"] = data["url"] or None
        entries.append(HistoryEntry(**data))
    return entries


def append_history(slug: str, entries: list[HistoryEntry]) -> int:
    """Append entries to history.md (creating file + header if needed). Returns count."""
    if not entries:
        return 0
    path = history_path(slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    with path.open("a", encoding="utf-8") as fh:
        if "| date | topic |" not in existing:
            if existing and not existing.endswith("\n"):
                fh.write("\n")
            fh.write(_HEADER)
        for entry in entries:
            fh.write(_row(entry))
    return len(entries)
