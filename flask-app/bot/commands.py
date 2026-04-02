"""Webex bot command handlers."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from shared.db import (
    projects_by_status, project_get, project_update,
    queue_list, queue_remove, queue_enqueue,
    config_get, config_set,
)


def handle_command(text):
    """Route command text to handler, return response string."""
    parts = text.strip().split(None, 1)
    cmd = parts[0].lower() if parts else ""
    arg = parts[1].strip() if len(parts) > 1 else ""

    handlers = {
        "status": cmd_status,
        "pause": cmd_pause,
        "resume": cmd_resume,
        "skip": cmd_skip,
        "restart": cmd_restart,
        "promote": cmd_promote,
        "help": cmd_help,
    }

    handler = handlers.get(cmd)
    if not handler:
        return f"Unknown command: `{cmd}`. Type `help` for available commands."

    return handler(arg)


def cmd_status(_arg):
    """Return queue and project status summary."""
    queued = queue_list()
    building = projects_by_status("building")
    deployed = projects_by_status("deployed-local")
    reviewing = projects_by_status("reviewing")
    paused = config_get("paused") == "true"

    lines = ["**Nightshift AutoFoundry Status**\n"]
    lines.append(f"Queue: **{len(queued)}** projects waiting")
    lines.append(f"Building: **{len(building)}** active sessions")
    lines.append(f"Deployed (local): **{len(deployed)}** ready for review")
    lines.append(f"In review: **{len(reviewing)}**")
    lines.append(f"Queue paused: **{'Yes' if paused else 'No'}**")

    if building:
        lines.append("\n**Active Builds:**")
        for p in building:
            phase = p.get("sdd_phase") or "starting"
            role = p.get("sdd_active_role") or "—"
            lines.append(f"- `{p['slug']}` — {phase} ({role})")

    if queued:
        lines.append(f"\n**Next in queue:** `{queued[0]['slug']}`")

    return "\n".join(lines)


def cmd_pause(_arg):
    config_set("paused", "true")
    return "Queue paused. Active builds will continue but no new projects will be dequeued."


def cmd_resume(_arg):
    config_set("paused", "false")
    return "Queue resumed. New projects will be dequeued as slots open."


def cmd_skip(slug):
    if not slug:
        return "Usage: `skip <project-slug>`"
    project = project_get(slug)
    if not project:
        return f"Project `{slug}` not found."
    if project["status"] not in ("queued", "building"):
        return f"Project `{slug}` is `{project['status']}` — can only skip queued or building projects."
    project_update(slug, status="scrapped")
    queue_remove(project["id"])
    return f"Project `{slug}` skipped and marked as scrapped."


def cmd_restart(slug):
    if not slug:
        return "Usage: `restart <project-slug>`"
    project = project_get(slug)
    if not project:
        return f"Project `{slug}` not found."
    project_update(slug, status="queued", stall_alerted=0, sdd_phase=None, sdd_active_role=None)
    queue_enqueue(project["id"])
    return f"Project `{slug}` re-queued for rebuild."


def cmd_promote(slug):
    if not slug:
        return "Usage: `promote <project-slug>`"
    project = project_get(slug)
    if not project:
        return f"Project `{slug}` not found."
    if project["status"] not in ("deployed-local", "reviewing"):
        return f"Project `{slug}` is `{project['status']}` — can only promote deployed or reviewing projects."
    project_update(slug, status="promoted")
    return f"Project `{slug}` marked for promotion to Render. Deployment will begin shortly."


def cmd_help(_arg):
    return """**Nightshift AutoFoundry Commands**

- `status` — Queue depth, active builds, recent completions
- `pause` — Stop dequeuing new projects
- `resume` — Resume dequeuing
- `skip <slug>` — Remove project from queue, mark as scrapped
- `restart <slug>` — Re-queue a stalled or failed project
- `promote <slug>` — Deploy a locally-tested project to Render
- `help` — Show this message"""
