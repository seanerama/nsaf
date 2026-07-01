"""Stage 4: profile scaffolding round-trips through the parser."""

from __future__ import annotations

import pytest

from daily_brief.paths import history_path, kb_path
from daily_brief.profiles import load_profile, parse_reference
from daily_brief.setup import ensure_general, general_reference, scaffold_profile


def test_general_reference_parses():
    p = parse_reference(general_reference())
    assert p.slug == "general"
    assert p.topics


def test_scaffold_empty_profile(data_dir):
    scaffold_profile("realtor", "Realtor", "a realtor who tracks local markets")
    p = load_profile("realtor")
    assert p.slug == "realtor"
    assert p.title == "Realtor"
    assert p.topics  # has at least the skeleton topic
    assert history_path("realtor").exists()
    assert kb_path("realtor").exists()


def test_scaffold_from_sample_has_multiple_topics(data_dir):
    scaffold_profile("ai", "AI", "an ai engineer", from_sample=True)
    p = load_profile("ai")
    names = [t.name for t in p.topics]
    assert "Model releases" in names and "AI agents" in names
    assert any(t.sources for t in p.topics)


def test_scaffold_refuses_overwrite_without_force(data_dir):
    scaffold_profile("x", "X", "d")
    with pytest.raises(FileExistsError):
        scaffold_profile("x", "X", "d")
    # force overwrites
    scaffold_profile("x", "X2", "d2", force=True)
    assert load_profile("x").title == "X2"


def test_ensure_general_idempotent(data_dir):
    a = ensure_general()
    b = ensure_general()
    assert a == b
    assert load_profile("general").slug == "general"
