"""Stage 1: reference.md parsing."""

from __future__ import annotations

from daily_brief.models import SourceType
from daily_brief.profiles import parse_reference

SAMPLE = """\
---
slug: ai-engineer
title: AI Engineer
description: ships LLM products and tracks the field
---

## Topics

### AI agents
- web_search: true
- source: Stratechery (blog) https://stratechery.com
- source: Latent Space (blog) https://latent.space
- this line is junk and should be ignored

### Model releases
- web_search: false
- source: Anthropic News (news)
"""


def test_parse_metadata():
    p = parse_reference(SAMPLE)
    assert p.slug == "ai-engineer"
    assert p.title == "AI Engineer"
    assert "ships LLM products" in p.description


def test_parse_topics_and_sources():
    p = parse_reference(SAMPLE)
    assert [t.name for t in p.topics] == ["AI agents", "Model releases"]

    agents = p.topics[0]
    assert agents.web_search is True
    assert len(agents.sources) == 2
    assert agents.sources[0].name == "Stratechery"
    assert agents.sources[0].type == SourceType.BLOG
    assert agents.sources[0].url == "https://stratechery.com"

    releases = p.topics[1]
    assert releases.web_search is False
    assert len(releases.sources) == 1
    assert releases.sources[0].url is None
    assert releases.sources[0].type == SourceType.NEWS


def test_unknown_source_type_falls_back_to_website():
    p = parse_reference(
        "---\nslug: x\ntitle: X\ndescription: d\n---\n\n### T\n- source: Foo (podcast) https://f.com\n"
    )
    assert p.topics[0].sources[0].type == SourceType.WEBSITE


def test_web_search_defaults_false():
    doc = "---\nslug: x\ntitle: X\ndescription: d\n---\n\n### T\n- source: Foo (blog)\n"
    p = parse_reference(doc)
    assert p.topics[0].web_search is False
