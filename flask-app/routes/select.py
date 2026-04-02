"""Idea selection routes."""

import json
import os
import re
from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from shared.db import ideas_for_date, project_create, queue_enqueue

select_bp = Blueprint("select", __name__)


def _slugify(name):
    """Convert app name to a URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")[:60]


@select_bp.route("/select", methods=["GET"])
def show_ideas():
    """Display today's ideas for selection."""
    today = request.args.get("date", date.today().isoformat())
    ideas = ideas_for_date(today)

    # Group by source
    grouped = {"openai": [], "gemini": [], "anthropic": []}
    for idea in ideas:
        source = idea.get("source", "unknown")
        if source in grouped:
            grouped[source].append(idea)

    return render_template("select.html", grouped=grouped, date=today, total=len(ideas))


@select_bp.route("/select", methods=["POST"])
def submit_selections():
    """Process selected ideas — create projects and queue them."""
    selected_ids = request.form.getlist("idea_ids")
    projects_dir = os.environ.get("NSAF_PROJECTS_DIR", "./projects")

    created = []
    for idea_id_str in selected_ids:
        idea_id = int(idea_id_str)
        # Get the idea to build the slug
        from shared.db import idea_get
        idea = idea_get(idea_id)
        if not idea:
            continue

        slug = _slugify(idea["name"])
        project_dir = os.path.join(projects_dir, slug)

        try:
            pid = project_create(slug, idea_id, project_dir)
            queue_enqueue(pid)
            created.append(slug)
        except Exception:
            # Duplicate slug — append id
            slug = f"{slug}-{idea_id}"
            project_dir = os.path.join(projects_dir, slug)
            pid = project_create(slug, idea_id, project_dir)
            queue_enqueue(pid)
            created.append(slug)

    return render_template("select.html", grouped={}, date="", total=0,
                           message=f"Queued {len(created)} projects: {', '.join(created)}")
