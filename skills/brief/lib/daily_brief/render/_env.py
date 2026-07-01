"""Shared Jinja2 environment + helpers for renderers."""

from __future__ import annotations

from collections import OrderedDict

from jinja2 import Environment, PackageLoader, select_autoescape

from ..models import BriefRun

_env = Environment(
    loader=PackageLoader("daily_brief", "templates"),
    autoescape=select_autoescape(["html", "xml", "j2"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def get_template(name: str):
    return _env.get_template(name)


def group_by_topic(run: BriefRun) -> list[dict]:
    """Group a run's items by topic name, preserving first-seen order."""
    groups: OrderedDict[str, list] = OrderedDict()
    for item in run.items:
        groups.setdefault(item.topic or "Other", []).append(item)
    return [{"name": name, "entries": entries} for name, entries in groups.items()]
