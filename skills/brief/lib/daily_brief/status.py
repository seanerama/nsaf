"""Gather workflow status across profiles (testable; CLI renders it)."""

from __future__ import annotations

import json

from .history import read_history
from .paths import briefs_root
from .profiles import list_profiles, load_profile


def _last_run(slug: str) -> dict | None:
    """Return info about the most recent run for a profile, or None."""
    runs_dir = briefs_root() / slug
    if not runs_dir.exists():
        return None
    timestamps = sorted(
        (d.name for d in runs_dir.iterdir() if d.is_dir()), reverse=True
    )
    for ts in timestamps:
        run_json = runs_dir / ts / "run.json"
        if not run_json.exists():
            continue
        try:
            data = json.loads(run_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        return {"timestamp": ts, "stats": data.get("stats", {}),
                "trigger": data.get("trigger", "")}
    return None


def gather_status() -> dict:
    """Build a status report dict for all profiles plus overall totals."""
    profiles = []
    total_history = 0
    total_runs = 0
    for slug, title in list_profiles():
        try:
            topics = len(load_profile(slug).topics)
        except Exception:
            topics = 0
        history_count = len(read_history(slug))
        last = _last_run(slug)
        total_history += history_count
        runs_dir = briefs_root() / slug
        run_count = sum(1 for d in runs_dir.iterdir() if d.is_dir()) if runs_dir.exists() else 0
        total_runs += run_count
        profiles.append({
            "slug": slug,
            "title": title,
            "topics": topics,
            "history_entries": history_count,
            "runs": run_count,
            "last_run": last,
        })
    return {
        "profiles": profiles,
        "totals": {
            "profiles": len(profiles),
            "history_entries": total_history,
            "runs": total_runs,
        },
    }
