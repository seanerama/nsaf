"""Pydantic data models — the central contract (see contracts/data-models.md).

Field names here are part of the contract; other modules and sub-agent return values
validate against these.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class SourceType(StrEnum):
    WEBSITE = "website"
    BLOG = "blog"
    NEWS = "news"
    WEB_SEARCH = "web-search"
    YOUTUBE = "youtube"  # reserved: accepted/stored but not ingested in v1


class Source(BaseModel):
    name: str
    type: SourceType
    url: str | None = None
    notes: str | None = None


class Topic(BaseModel):
    name: str
    sources: list[Source] = Field(default_factory=list)
    web_search: bool = False


class Profile(BaseModel):
    slug: str
    title: str
    description: str
    topics: list[Topic] = Field(default_factory=list)


class PriorCoverage(BaseModel):
    source: str
    date: str


class BriefItem(BaseModel):
    id: str
    title: str
    summary: str = ""
    why_it_matters: str = ""
    source: Source
    url: str | None = None
    published: str | None = None
    topic: str = ""
    prior_coverage: list[PriorCoverage] = Field(default_factory=list)


class HistoryEntry(BaseModel):
    date: str
    topic: str
    title: str
    source: str
    url: str | None = None
    dedup_key: str


class Failure(BaseModel):
    source: str
    reason: str


class BriefRun(BaseModel):
    profile: str
    trigger: str  # "run" | "topic"
    requested_topic: str | None = None
    started_at: str
    items: list[BriefItem] = Field(default_factory=list)
    failures: list[Failure] = Field(default_factory=list)
    stats: dict[str, int] = Field(default_factory=dict)
