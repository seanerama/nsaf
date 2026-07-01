"""Interactive self-contained HTML renderer."""

from __future__ import annotations

from ..models import BriefRun
from ._env import get_template, group_by_topic


def render_html(run: BriefRun) -> str:
    """Render a BriefRun into a single self-contained interactive HTML document."""
    topics = group_by_topic(run)
    sources = sorted({i.source.name for i in run.items})
    dates = sorted({i.published for i in run.items if i.published}, reverse=True)
    run_id = f"{run.profile}:{run.started_at}"
    title = run.requested_topic or f"{run.profile.title()} brief"
    return get_template("brief.html.j2").render(
        run=run,
        run_id=run_id,
        title=title,
        topics=topics,
        sources=sources,
        dates=dates,
    )
