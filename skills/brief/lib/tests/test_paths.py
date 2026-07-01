"""Stage 1: path helpers honor BRIEF_DATA_DIR."""

from __future__ import annotations

from pathlib import Path

from daily_brief import paths


def test_default_root(monkeypatch):
    monkeypatch.delenv("BRIEF_DATA_DIR", raising=False)
    assert paths.data_root() == Path("data")


def test_override_root(monkeypatch, tmp_path):
    monkeypatch.setenv("BRIEF_DATA_DIR", str(tmp_path))
    assert paths.data_root() == tmp_path
    assert paths.reference_path("general") == tmp_path / "profiles" / "general" / "reference.md"
    assert paths.history_path("general") == tmp_path / "profiles" / "general" / "history.md"
    assert paths.kb_path("general") == tmp_path / "profiles" / "general" / "knowledge-base.md"
    assert paths.brief_dir("general", "2026-06-29-1030") == (
        tmp_path / "briefs" / "general" / "2026-06-29-1030"
    )
