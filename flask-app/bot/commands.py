"""Webex bot command handlers."""

import json
import os
import subprocess
import sys
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from shared.db import (
    projects_by_status, project_get, project_update,
    queue_list, queue_remove, queue_enqueue,
    config_get, config_set,
    ideas_for_date, idea_get,
    project_create, get_db,
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
        "ideas": cmd_ideas,
        "idea": cmd_idea_detail,
        "generate": cmd_generate,
        "queue": cmd_queue_idea,
        "system": cmd_system,
        "tokens": cmd_tokens,
        "debug": cmd_debug,
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
    promoted = projects_by_status("promoted")
    paused = config_get("paused") == "true"

    lines = ["**Nightshift AutoFoundry Status**\n"]
    lines.append(f"Queue: **{len(queued)}** projects waiting")
    lines.append(f"Building: **{len(building)}** active sessions")
    lines.append(f"Deployed (local): **{len(deployed)}** ready for review")
    lines.append(f"In review: **{len(reviewing)}**")
    lines.append(f"Promoted: **{len(promoted)}**")
    lines.append(f"Queue paused: **{'Yes' if paused else 'No'}**")

    if building:
        lines.append("\n**Active Builds:**")
        for p in building:
            phase = p.get("sdd_phase") or "starting"
            role = p.get("sdd_active_role") or "—"
            progress = p.get("sdd_progress") or 0
            lines.append(f"- `{p['slug']}` — {phase} ({role}) [{progress}%]")

    if deployed:
        lines.append("\n**Ready for Review:**")
        for p in deployed:
            url = p.get("deployed_url") or "—"
            lines.append(f"- `{p['slug']}` — {url}")

    if queued:
        lines.append(f"\n**Next in queue:** `{queued[0]['slug']}`")

    return "\n".join(lines)


def cmd_ideas(arg):
    """List today's ideas with status. Supports: 'ideas', 'ideas 2', 'ideas openai', 'ideas 2026-04-01'."""
    parts = arg.split() if arg else []
    target_date = date.today().isoformat()
    page = 1
    source_filter = None

    for p in parts:
        if p.isdigit() and len(p) <= 2:
            page = int(p)
        elif len(p) == 10 and p[4:5] == '-':
            target_date = p
        elif p.lower() in ("openai", "gemini", "anthropic"):
            source_filter = p.lower()

    ideas = ideas_for_date(target_date)
    if not ideas:
        return f"No ideas found for {target_date}. Run `generate` to create new ideas."

    # Get all projects to check which ideas are queued/built
    db = get_db()
    projects = db.execute("SELECT idea_id, slug, status FROM projects").fetchall()
    idea_status = {p["idea_id"]: (p["slug"], p["status"]) for p in projects}

    # Filter by source if requested
    if source_filter:
        ideas = [i for i in ideas if i.get("source") == source_filter]

    # Paginate — 10 ideas per page to stay under Webex message limit
    per_page = 10
    total_pages = max(1, (len(ideas) + per_page - 1) // per_page)
    page = min(page, total_pages)
    start = (page - 1) * per_page
    page_ideas = ideas[start:start + per_page]

    lines = [f"**Nightshift AutoFoundry — Ideas for {target_date}** (page {page}/{total_pages})\n"]

    for idea in page_ideas:
        status_icon = "⬜"
        status_text = ""
        if idea["id"] in idea_status:
            slug, st = idea_status[idea["id"]]
            status_map = {
                "building": ("🔨", " → building"),
                "deployed-local": ("✅", " → deployed"),
                "reviewing": ("✅", " → reviewing"),
                "promoted": ("🚀", " → promoted"),
                "queued": ("⏳", " → queued"),
                "scrapped": ("❌", " → scrapped"),
            }
            status_icon, status_text = status_map.get(st, ("⬜", ""))

        source_tag = idea.get("source", "?")[0].upper()
        lines.append(f"- {status_icon} **#{idea['id']}** [{source_tag}] {idea['name']}{status_text}")

    lines.append(f"\n{len(ideas)} ideas total. `idea <id>` for details, `queue <id>` to build.")
    if total_pages > 1:
        lines.append(f"`ideas {page + 1}` next page. `ideas openai` / `ideas gemini` / `ideas anthropic` to filter.")

    return "\n".join(lines)


def cmd_idea_detail(arg):
    """Show details for a specific idea."""
    if not arg:
        return "Usage: `idea <id>`"
    try:
        idea_id = int(arg)
    except ValueError:
        return f"Invalid idea ID: `{arg}`"

    idea = idea_get(idea_id)
    if not idea:
        return f"Idea #{idea_id} not found."

    # Check if this idea has a project
    db = get_db()
    project = db.execute(
        "SELECT slug, status, deployed_url, sdd_phase, sdd_active_role, sdd_progress FROM projects WHERE idea_id = ?",
        (idea_id,)
    ).fetchone()

    stack = idea.get("suggested_stack", "{}")
    if isinstance(stack, str):
        try:
            stack = json.loads(stack)
        except (json.JSONDecodeError, TypeError):
            stack = {}
    stack_str = ", ".join(f"{v}" for v in stack.values()) if stack else "—"

    lines = [f"**Idea #{idea_id}: {idea['name']}**\n"]
    lines.append(f"**Description:** {idea['description']}")
    lines.append(f"**Category:** {idea['category']}")
    lines.append(f"**Complexity:** {idea['complexity']}")
    lines.append(f"**Source:** {idea['source']}")
    lines.append(f"**Stack:** {stack_str}")
    lines.append(f"**Generated:** {idea['date']}")

    if project:
        slug = project["slug"]
        status = project["status"]
        lines.append(f"\n**Build Status:** `{status}`")
        lines.append(f"**Project:** `{slug}`")
        if project["sdd_phase"]:
            lines.append(f"**Phase:** {project['sdd_phase']} ({project['sdd_active_role'] or '—'}) [{project['sdd_progress'] or 0}%]")
        if project["deployed_url"]:
            lines.append(f"**Local URL:** {project['deployed_url']}")
    else:
        lines.append(f"\n**Build Status:** not queued")
        lines.append(f"Use `queue {idea_id}` to add to build queue.")

    return "\n".join(lines)


def _slugify(name):
    """Convert app name to a URL-safe slug."""
    import re
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")[:60]


def cmd_queue_idea(arg):
    """Add an idea to the build queue."""
    if not arg:
        return "Usage: `queue <idea-id>`"
    try:
        idea_id = int(arg)
    except ValueError:
        return f"Invalid idea ID: `{arg}`"

    idea = idea_get(idea_id)
    if not idea:
        return f"Idea #{idea_id} not found."

    # Check if already queued
    db = get_db()
    existing = db.execute("SELECT slug, status FROM projects WHERE idea_id = ?", (idea_id,)).fetchone()
    if existing:
        return f"Idea #{idea_id} already has project `{existing['slug']}` ({existing['status']})."

    slug = _slugify(idea["name"])
    projects_dir = os.environ.get("NSAF_PROJECTS_DIR", "./projects")
    project_dir = os.path.join(projects_dir, slug)

    import sqlite3
    try:
        pid = project_create(slug, idea_id, project_dir)
    except sqlite3.IntegrityError:
        slug = f"{slug}-{idea_id}"
        project_dir = os.path.join(projects_dir, slug)
        pid = project_create(slug, idea_id, project_dir)

    queue_enqueue(pid)
    return f"Idea #{idea_id} (**{idea['name']}**) queued as `{slug}`. It will build when a slot opens."


def cmd_generate(_arg):
    """Trigger idea generation."""
    nsaf_dir = os.environ.get("NSAF_DIR", os.path.join(os.path.dirname(__file__), "..", ".."))
    venv_python = os.path.join(nsaf_dir, "venv", "bin", "python")
    script = os.path.join(nsaf_dir, "idea-generator", "generate.py")

    if not os.path.exists(script):
        return f"Generator script not found at `{script}`"

    try:
        result = subprocess.Popen(
            [venv_python, script],
            cwd=nsaf_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return f"Idea generation started (PID {result.pid}). Check back in a minute with `ideas`."
    except Exception as e:
        return f"Failed to start generation: {e}"


def cmd_debug(arg):
    """Spawn a Claude Code session to debug a deployed project."""
    if not arg:
        return "Usage: `debug <slug> <description of the problem>`\nExample: `debug learnloop page shows blank white screen`"

    parts = arg.split(None, 1)
    slug = parts[0]
    issue = parts[1] if len(parts) > 1 else "The app is not working correctly. Diagnose and fix the issue."

    project = project_get(slug)
    if not project:
        return f"Project `{slug}` not found."

    project_dir = project.get("project_dir", "")
    if not project_dir or not os.path.isdir(project_dir):
        return f"Project directory for `{slug}` not found at `{project_dir}`."

    deployed_url = project.get("deployed_url", "")

    # Build the debug prompt
    prompt = (
        f"You are debugging a deployed web app. The project is at {project_dir}. "
        f"The app should be running at {deployed_url}. "
        f"\n\nPROBLEM REPORTED BY USER: {issue}"
        f"\n\nDiagnose the issue, fix it, and verify the fix. "
        f"Check logs, test endpoints, read error output. "
        f"If the app isn't running, start it. "
        f"If there are code bugs, fix them and restart the app. "
        f"Report what you found and what you fixed."
    )

    claude_bin = os.environ.get("NSAF_CLAUDE_COMMAND", "claude").split()[0]
    debug_log = os.path.join(project_dir, "debug.log")

    try:
        proc = subprocess.Popen(
            [claude_bin, "-p", prompt, "--dangerously-skip-permissions"],
            cwd=project_dir,
            stdout=open(debug_log, "w"),
            stderr=subprocess.STDOUT,
        )
        return (
            f"Debug session started for `{slug}` (PID {proc.pid}).\n\n"
            f"**Issue:** {issue}\n"
            f"**Log:** `{debug_log}`\n\n"
            f"Claude is investigating. Check back in a few minutes — "
            f"the fix will be applied automatically."
        )
    except Exception as e:
        return f"Failed to start debug session: {e}"


def cmd_system(_arg):
    """Show system resource usage."""
    lines = ["**Nightshift AutoFoundry — System Status**\n"]

    # CPU and memory
    try:
        import shutil
        load1, load5, load15 = os.getloadavg()
        lines.append(f"**Load avg:** {load1:.1f} / {load5:.1f} / {load15:.1f}")
    except OSError:
        pass

    # Memory
    try:
        with open("/proc/meminfo") as f:
            mem = {}
            for line in f:
                parts = line.split()
                if parts[0] in ("MemTotal:", "MemAvailable:"):
                    mem[parts[0].rstrip(":")] = int(parts[1])
            if "MemTotal" in mem and "MemAvailable" in mem:
                total_gb = mem["MemTotal"] / 1024 / 1024
                avail_gb = mem["MemAvailable"] / 1024 / 1024
                used_pct = ((mem["MemTotal"] - mem["MemAvailable"]) / mem["MemTotal"]) * 100
                lines.append(f"**Memory:** {total_gb - avail_gb:.1f}GB / {total_gb:.1f}GB ({used_pct:.0f}% used)")
    except Exception:
        pass

    # Disk
    try:
        import shutil
        nsaf_dir = os.environ.get("NSAF_DIR", os.path.join(os.path.dirname(__file__), "..", ".."))
        usage = shutil.disk_usage(nsaf_dir)
        total_gb = usage.total / 1024**3
        used_gb = usage.used / 1024**3
        pct = (usage.used / usage.total) * 100
        lines.append(f"**Disk:** {used_gb:.0f}GB / {total_gb:.0f}GB ({pct:.0f}% used)")
    except Exception:
        pass

    # Claude processes
    try:
        result = subprocess.run(
            ["pgrep", "-c", "-f", "claude.*dangerously"],
            capture_output=True, text=True
        )
        count = int(result.stdout.strip()) if result.returncode == 0 else 0
        lines.append(f"**Claude sessions:** {count} running")
    except Exception:
        pass

    # Project counts
    db = get_db()
    counts = db.execute(
        "SELECT status, COUNT(*) as c FROM projects GROUP BY status"
    ).fetchall()
    if counts:
        lines.append("\n**Projects:**")
        for row in counts:
            lines.append(f"- {row['status']}: {row['c']}")

    # Queue depth
    q = queue_list()
    lines.append(f"\n**Queue depth:** {len(q)}")

    return "\n".join(lines)


def cmd_tokens(arg):
    """Show token/cost estimates from build logs."""
    hours = 24
    if arg:
        try:
            hours = int(arg)
        except ValueError:
            return "Usage: `tokens [hours]` — e.g. `tokens 4`, `tokens 12`, `tokens 24`"

    cutoff = datetime.utcnow() - timedelta(hours=hours)
    db = get_db()

    # Count projects active in the time window
    projects = db.execute(
        "SELECT slug, status, started_at, completed_at FROM projects WHERE started_at IS NOT NULL"
    ).fetchall()

    active_in_window = []
    for p in projects:
        started = datetime.fromisoformat(p["started_at"].replace("Z", "+00:00")).replace(tzinfo=None) if p["started_at"] else None
        if started and started >= cutoff:
            active_in_window.append(p)

    # Check build log sizes as a rough proxy
    projects_dir = os.environ.get("NSAF_PROJECTS_DIR", "./projects")
    total_log_bytes = 0
    for p in active_in_window:
        log_path = os.path.join(projects_dir, p["slug"], "build.log")
        try:
            total_log_bytes += os.path.getsize(log_path)
        except OSError:
            pass

    lines = [f"**Nightshift AutoFoundry — Activity (last {hours}h)**\n"]
    lines.append(f"**Projects started:** {len(active_in_window)}")

    completed = [p for p in active_in_window if p["status"] in ("deployed-local", "reviewing", "promoted")]
    building = [p for p in active_in_window if p["status"] == "building"]
    failed = [p for p in active_in_window if p["status"] in ("queued", "scrapped")]

    lines.append(f"**Completed:** {len(completed)}")
    lines.append(f"**Building:** {len(building)}")
    lines.append(f"**Failed/scrapped:** {len(failed)}")

    if active_in_window:
        lines.append(f"\n**Build log output:** {total_log_bytes / 1024:.0f} KB")
        lines.append("\n**Projects:**")
        for p in active_in_window:
            icon = {"building": "🔨", "deployed-local": "✅", "reviewing": "👀", "promoted": "🚀", "scrapped": "❌"}.get(p["status"], "⏳")
            lines.append(f"- {icon} `{p['slug']}` — {p['status']}")

    lines.append(f"\n_Note: Exact token counts require Claude API billing dashboard. This shows build activity as a proxy._")

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

**Build Management**
- `status` — Queue depth, active builds, completions
- `pause` / `resume` — Control the build queue
- `skip <slug>` — Scrap a project
- `restart <slug>` — Re-queue a stalled project
- `promote <slug>` — Deploy to Render

**Ideas**
- `ideas` — List today's ideas with build status
- `ideas YYYY-MM-DD` — List ideas for a specific date
- `idea <id>` — Detailed view of an idea
- `queue <id>` — Add an idea to the build queue
- `generate` — Trigger new idea generation

**Troubleshooting**
- `debug <slug> <problem>` — Spawn Claude to diagnose and fix a deployed app

**Monitoring**
- `system` — CPU, memory, disk, active sessions
- `tokens [hours]` — Build activity (default 24h)
- `help` — Show this message"""
