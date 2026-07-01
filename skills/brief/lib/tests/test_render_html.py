"""Stage 3: interactive HTML renderer."""

from __future__ import annotations

from daily_brief.render import render_html

from .fixtures import sample_run


def test_html_contains_items_and_framing():
    html = render_html(sample_run())
    assert "Anthropic ships Opus 4.8" in html
    assert "The agent platform wars" in html
    assert "changes your model-selection defaults" in html  # why_it_matters
    assert "Why this matters" in html


def test_html_has_prior_coverage_note():
    html = render_html(sample_run())
    assert "Also covered by" in html
    assert "TechCrunch on 2026-06-20" in html


def test_html_is_self_contained():
    html = render_html(sample_run())
    assert "<!DOCTYPE html>" in html
    assert "http-equiv" not in html
    # No external stylesheet/script references.
    assert "src=\"http" not in html and "href=\"http" not in html.split("<main>")[0]


def test_html_has_search_and_localstorage():
    html = render_html(sample_run())
    assert 'id="search"' in html
    assert "localStorage" in html
    assert "brief-read:" in html


def test_html_groups_by_topic_and_has_audio_player():
    html = render_html(sample_run())
    assert 'data-topic="Model releases"' in html
    assert 'data-topic="AI agents"' in html
    assert "<audio" in html


def test_html_lists_failures():
    html = render_html(sample_run())
    assert "Could not fetch" in html
    assert "Paywalled Times" in html
