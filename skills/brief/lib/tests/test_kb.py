"""Stage 2: knowledge base append."""

from __future__ import annotations

from daily_brief.knowledge_base import append_kb
from daily_brief.paths import kb_path


def test_append_kb_writes_dated_section(data_dir):
    n = append_kb("general", ["learned A", "learned B"], "2026-06-29")
    assert n == 2
    text = kb_path("general").read_text(encoding="utf-8")
    assert "## 2026-06-29" in text
    assert "- learned A" in text
    assert "- learned B" in text


def test_append_kb_empty_is_noop(data_dir):
    assert append_kb("general", ["  ", ""], "2026-06-29") == 0
    assert not kb_path("general").exists()


def test_append_kb_accumulates(data_dir):
    append_kb("general", ["a"], "2026-06-28")
    append_kb("general", ["b"], "2026-06-29")
    text = kb_path("general").read_text(encoding="utf-8")
    assert "## 2026-06-28" in text and "## 2026-06-29" in text
