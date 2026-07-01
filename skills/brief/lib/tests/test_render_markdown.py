"""Stage 3: markdown summary renderer."""

from __future__ import annotations

from daily_brief.render import render_summary

from .fixtures import sample_run


def test_summary_groups_by_topic():
    md = render_summary(sample_run())
    assert "## Model releases" in md
    assert "## AI agents" in md


def test_summary_has_titles_and_why():
    md = render_summary(sample_run())
    assert "### Anthropic ships Opus 4.8" in md
    assert "**Why this matters:**" in md
    assert "changes your model-selection defaults" in md


def test_summary_has_source_links_and_prior():
    md = render_summary(sample_run())
    assert "[Perplexity](https://example.com/opus)" in md
    assert "Prior coverage:" in md


def test_summary_lists_failures():
    md = render_summary(sample_run())
    assert "Could not fetch" in md
