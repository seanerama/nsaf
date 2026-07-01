"""Podcast deep-dive prompt builder (NotebookLM-style two-host script)."""

from __future__ import annotations

from ..models import Profile

_TEMPLATE = """\
You are scripting a NotebookLM-style podcast: two hosts (Host A, an upbeat curious guide, and
Host B, a sharp analyst) doing a friendly but substantive deep dive into today's brief.

Audience lens — the listener is: {description}
Frame the conversation so every segment answers "why does this matter to me, in that role?"

Write a natural two-host dialogue script (label lines "Host A:" / "Host B:"). Open with a
quick hook, walk through the items below grouped by topic, draw connections between them,
surface the "why it matters" angle, and close with a short recap of what to watch next.
Keep it conversational, ~6-10 minutes of spoken content. Do NOT invent facts beyond the
brief; if something is uncertain, say so.

=== TODAY'S BRIEF (markdown summary) ===
{summary}
=== END BRIEF ===

Output ONLY the script (markdown, host-labeled lines). No preamble.
"""


def build_podcast_prompt(summary_md: str, profile: Profile) -> str:
    """Build the deep-dive prompt handed to the podcast-script sub-agent."""
    return _TEMPLATE.format(description=profile.description.strip(), summary=summary_md.strip())
