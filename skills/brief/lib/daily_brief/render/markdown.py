"""Markdown summary renderer."""

from __future__ import annotations

from ..models import BriefRun
from ._env import get_template, group_by_topic


def render_summary(run: BriefRun) -> str:
    """Render a BriefRun into a clean markdown summary grouped by topic."""
    return get_template("summary.md.j2").render(run=run, topics=group_by_topic(run))
