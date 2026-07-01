"""Shared fixture builders for renderer/orchestration tests."""

from __future__ import annotations

from daily_brief.models import (
    BriefItem,
    BriefRun,
    Failure,
    PriorCoverage,
    Profile,
    Source,
    SourceType,
    Topic,
)


def sample_run() -> BriefRun:
    return BriefRun(
        profile="ai-engineer",
        trigger="run",
        started_at="2026-06-29T09:00:00",
        items=[
            BriefItem(
                id="url:https://example.com/opus",
                title="Anthropic ships Opus 4.8",
                summary="A faster Opus with a 1M context window.",
                why_it_matters="As an AI engineer this changes your model-selection defaults.",
                source=Source(name="Perplexity", type=SourceType.WEB_SEARCH),
                url="https://example.com/opus",
                published="2026-06-28",
                topic="Model releases",
                prior_coverage=[PriorCoverage(source="TechCrunch", date="2026-06-20")],
            ),
            BriefItem(
                id="url:https://stratechery.com/agents",
                title="The agent platform wars",
                summary="Why orchestration is the new moat.",
                why_it_matters="Helps you decide where to invest your agent stack.",
                source=Source(name="Stratechery", type=SourceType.BLOG),
                url="https://stratechery.com/agents",
                published="2026-06-27",
                topic="AI agents",
            ),
        ],
        failures=[Failure(source="Paywalled Times", reason="login required")],
        stats={"items_total": 2, "items_new": 1, "items_prior": 1},
    )


def sample_profile() -> Profile:
    return Profile(
        slug="ai-engineer",
        title="AI Engineer",
        description="An AI engineer who ships LLM products and tracks the field.",
        topics=[Topic(name="Model releases", web_search=True)],
    )
