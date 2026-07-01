"""Stage 1: every model constructs and round-trips JSON."""

from __future__ import annotations

from daily_brief.models import (
    BriefItem,
    BriefRun,
    Failure,
    HistoryEntry,
    PriorCoverage,
    Profile,
    Source,
    SourceType,
    Topic,
)


def test_source_roundtrip():
    s = Source(name="Stratechery", type=SourceType.BLOG, url="https://stratechery.com")
    assert Source.model_validate(s.model_dump()) == s
    assert s.type == "blog"


def test_youtube_type_accepted():
    s = Source(name="Some Channel", type=SourceType.YOUTUBE, url="https://youtube.com/@x")
    assert s.type == SourceType.YOUTUBE


def test_profile_roundtrip():
    p = Profile(
        slug="ai-engineer",
        title="AI Engineer",
        description="ships LLM products",
        topics=[Topic(name="AI agents", web_search=True,
                      sources=[Source(name="X", type=SourceType.BLOG)])],
    )
    assert Profile.model_validate(p.model_dump()) == p


def test_briefitem_and_run_roundtrip():
    item = BriefItem(
        id="key1",
        title="Big news",
        summary="something happened",
        why_it_matters="it helps you because...",
        source=Source(name="Perplexity", type=SourceType.WEB_SEARCH),
        topic="AI agents",
        prior_coverage=[PriorCoverage(source="X", date="2026-06-01")],
    )
    run = BriefRun(
        profile="general",
        trigger="topic",
        requested_topic="AI agents",
        started_at="2026-06-29T10:00:00",
        items=[item],
        failures=[Failure(source="Y", reason="timeout")],
        stats={"items_total": 1},
    )
    parsed = BriefRun.model_validate_json(run.model_dump_json())
    assert parsed == run
    assert parsed.items[0].prior_coverage[0].source == "X"


def test_history_entry_roundtrip():
    h = HistoryEntry(date="2026-06-29", topic="t", title="ti", source="s",
                     url=None, dedup_key="k")
    assert HistoryEntry.model_validate(h.model_dump()) == h
