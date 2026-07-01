"""Stage 2: append-only history round-trip."""

from __future__ import annotations

from daily_brief.history import append_history, read_history
from daily_brief.models import HistoryEntry
from daily_brief.paths import history_path


def _entry(title, key, source="S", date="2026-06-29"):
    return HistoryEntry(date=date, topic="t", title=title, source=source,
                        url="https://example.com/x", dedup_key=key)


def test_append_then_read_roundtrip(data_dir):
    append_history("general", [_entry("A", "k1"), _entry("B", "k2")])
    rows = read_history("general")
    assert [r.title for r in rows] == ["A", "B"]
    assert [r.dedup_key for r in rows] == ["k1", "k2"]


def test_header_written_once_and_appends_accumulate(data_dir):
    append_history("general", [_entry("A", "k1")])
    append_history("general", [_entry("B", "k2")])
    text = history_path("general").read_text(encoding="utf-8")
    assert text.count("| date | topic |") == 1
    assert len(read_history("general")) == 2


def test_read_missing_returns_empty(data_dir):
    assert read_history("nope") == []


def test_pipe_in_title_is_sanitized(data_dir):
    append_history("general", [_entry("A | B | C", "k1")])
    rows = read_history("general")
    assert rows[0].title == "A | B | C"


def test_append_empty_is_noop(data_dir):
    assert append_history("general", []) == 0
    assert read_history("general") == []
