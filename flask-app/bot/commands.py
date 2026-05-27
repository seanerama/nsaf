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
    story_ideas_for_date, story_idea_get,
    study_ideas_for_date, study_idea_get,
    ensure_project_idea_link_columns,
    vision_insert, vision_get, vision_update, vision_list,
)


def handle_command(text, attachments=None):
    """Route command text to handler, return response string."""
    parts = text.strip().split(None, 1)
    cmd = parts[0].lower() if parts else ""
    arg = parts[1].strip() if len(parts) > 1 else ""

    handlers = {
        "status": cmd_status,
        "pause": cmd_pause,
        "pauseall": cmd_pauseall,
        "resume": cmd_resume,
        "skip": cmd_skip,
        "restart": cmd_restart,
        "promote": cmd_promote,
        "demote": cmd_demote,
        "ideas": cmd_ideas,
        "idea": cmd_idea,
        "stories": cmd_stories,
        "studies": cmd_studies,
        "generate": cmd_generate,
        "queue": cmd_queue_idea,
        "export": cmd_export,
        "delete": cmd_delete,
        "rebuild": cmd_rebuild,
        "modify": cmd_modify,
        "archive": cmd_archive,
        "gitpush": cmd_gitpush,
        "sws": cmd_sws,
        "story": cmd_story,
        "fetchstory": cmd_fetchstory,
        "storyfix": cmd_storyfix,
        "vision": cmd_vision,
        "stopall": cmd_stopall,
        "stop": cmd_stop,
        "start": cmd_start,
        "system": cmd_system,
        "tokens": cmd_tokens,
        "debug": cmd_debug,
        "help": cmd_help,
    }

    handler = handlers.get(cmd)
    if not handler:
        return f"Unknown command: `{cmd}`. Type `help` for available commands."

    # Pass attachments to commands that support them
    if cmd in ("sws", "vision") and attachments:
        return handler(arg, attachments=attachments)
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
        recent = sorted(
            deployed,
            key=lambda p: p.get("completed_at") or p.get("last_state_change") or "",
            reverse=True,
        )[:10]
        header = "\n**Ready for Review (last 10):**" if len(deployed) > 10 else "\n**Ready for Review:**"
        lines.append(header)
        for p in recent:
            url = p.get("deployed_url") or "—"
            lines.append(f"- `{p['slug']}` — {url}")
        if len(deployed) > 10:
            lines.append(f"_…{len(deployed) - 10} more. Use `export` for the full list._")

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
        tier = idea.get("tier", "") or ""
        tier_tag = f" `{tier}`" if tier else ""
        lines.append(f"- {status_icon} **#{idea['id']}** [{source_tag}]{tier_tag} {idea['name']}{status_text}")

    lines.append(f"\n{len(ideas)} ideas total. `idea <id>` for details, `queue <id>` to build.")
    if total_pages > 1:
        lines.append(f"`ideas {page + 1}` next page. `ideas openai` / `ideas gemini` / `ideas anthropic` to filter.")

    return "\n".join(lines)


def _parse_kind_args(arg):
    """Pull a leading kind keyword (story/study) off arg.

    Returns (kind, remainder). kind is 'app' (default), 'story', or 'study'.
    """
    parts = (arg or "").strip().split(None, 1)
    if not parts:
        return "app", ""
    head = parts[0].lower()
    if head in ("story", "stories"):
        return "story", parts[1].strip() if len(parts) > 1 else ""
    if head in ("study", "studies"):
        return "study", parts[1].strip() if len(parts) > 1 else ""
    return "app", arg.strip()


def _list_kind_ideas(arg, *, kind, label, fetch_for_date, link_col):
    """Shared listing for stories/studies. Mirrors cmd_ideas paging/filter."""
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

    ideas = fetch_for_date(target_date)
    if not ideas:
        return f"No {label} ideas found for {target_date}. Run `generate {kind}s` to create new ideas."

    ensure_project_idea_link_columns()
    db = get_db()
    project_rows = db.execute(
        f"SELECT {link_col} as iid, slug, status FROM projects WHERE {link_col} IS NOT NULL"
    ).fetchall()
    idea_status = {p["iid"]: (p["slug"], p["status"]) for p in project_rows}

    if source_filter:
        ideas = [i for i in ideas if i.get("source") == source_filter]

    per_page = 10
    total_pages = max(1, (len(ideas) + per_page - 1) // per_page)
    page = min(page, total_pages)
    start = (page - 1) * per_page
    page_ideas = ideas[start:start + per_page]

    plural = f"{label} ideas"
    list_cmd = "stories" if kind == "story" else "studies"
    lines = [f"**NSAF — {plural} for {target_date}** (page {page}/{total_pages})\n"]

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
                "complete": ("✅", " → complete"),
            }
            status_icon, status_text = status_map.get(st, ("⬜", f" → {st}"))
            status_text += f" `{slug}`"

        source_tag = idea.get("source", "?")[0].upper()
        tier = idea.get("tier", "") or ""
        tier_tag = f" `{tier}`" if tier else ""
        lines.append(f"- {status_icon} **#{idea['id']}** [{source_tag}]{tier_tag} {idea['name']}{status_text}")

    lines.append(
        f"\n{len(ideas)} {plural} total. "
        f"`idea {kind} <id>` for details, `queue {kind} <id>` to build."
    )
    if total_pages > 1:
        lines.append(f"`{list_cmd} {page + 1}` next page. `{list_cmd} openai` / gemini / anthropic to filter.")

    return "\n".join(lines)


def cmd_stories(arg):
    """List today's story ideas. Supports: 'stories', 'stories 2', 'stories openai', 'stories 2026-04-01'."""
    return _list_kind_ideas(
        arg, kind="story", label="story",
        fetch_for_date=story_ideas_for_date, link_col="story_idea_id",
    )


def cmd_studies(arg):
    """List today's study ideas. Supports: 'studies', 'studies 2', 'studies openai', 'studies 2026-04-01'."""
    return _list_kind_ideas(
        arg, kind="study", label="study",
        fetch_for_date=study_ideas_for_date, link_col="study_idea_id",
    )


def cmd_idea(arg, attachments=None):
    """Route `idea` command.

    - `idea <id>` or `idea story <id>` / `idea study <id>` → detail
    - `idea <free-form text>` → brainstorm a new vision session via Claude
    """
    if not arg or not arg.strip():
        return ("Usage:\n"
                "  `idea <id>` — show details for a generated idea\n"
                "  `idea story <id>` / `idea study <id>` — kind-specific details\n"
                "  `idea <free-form text>` — brainstorm a new idea with the bot")
    kind, rest = _parse_kind_args(arg)
    first = rest.split(None, 1)[0] if rest else ""
    if first.isdigit():
        return cmd_idea_detail(arg)
    return cmd_idea_brainstorm(arg, attachments=attachments)


def cmd_idea_brainstorm(raw_text, attachments=None):
    """Take a free-form idea, ask Claude to expand it, save as a vision session."""
    from bot.vision import expand_idea

    raw_text = raw_text.strip()
    if len(raw_text) < 10:
        return "Give me a bit more — at least a sentence or two so I can work with it."

    try:
        result = expand_idea(raw_text)
    except Exception as e:
        return f"Couldn't expand that idea — {e}\nTry again with a bit more context?"

    base = _slug_from_idea(result.get("title") or raw_text)
    slug = base or "untitled"
    n = 2
    while vision_get(slug):
        slug = f"{base}-{n}"
        n += 1

    vision_insert({
        "slug": slug,
        "raw_idea": raw_text,
        "interpretation": result["interpretation"],
        "proposed_kind": result["proposed_kind"],
        "vision_md": result["vision_md"],
        "status": "drafted",
    })

    lines = [
        f"**Idea captured as `{slug}`**",
        "",
        f"_{result['interpretation']}_",
        "",
        f"**Best-fit kind:** `{result['proposed_kind']}`",
        "",
        "I've drafted a vision doc with follow-up questions. What's next?",
        "",
        f"- `vision email {slug}` — email the .md to you (edit, re-upload later)",
        f"- `vision show {slug}` — render the doc here in Webex",
        f"- `vision build {slug}` — skip the questions and build it now",
        f"- `vision cancel {slug}` — drop it",
    ]
    return "\n".join(lines)


def _extract_title(md):
    """First H1 from a markdown doc."""
    import re
    if not md:
        return None
    m = re.search(r"^#\s+(.+)$", md, re.MULTILINE)
    return m.group(1).strip() if m else None


def _extract_section(md, section_name):
    """Return the body of `## <section_name>` (text up to the next ## heading)."""
    import re
    if not md:
        return None
    # [ \t]* on the heading line so we don't greedily consume blank lines too.
    pattern = rf"^##[ \t]+{re.escape(section_name)}[ \t]*\n([\s\S]*?)(?=^##[ \t]+|\Z)"
    m = re.search(pattern, md, re.MULTILINE)
    return m.group(1).strip() if m else None


def _replace_section(md, section_name, new_body):
    """Replace the body of `## <section_name>`. Append the section if missing."""
    import re
    pattern = rf"(^##[ \t]+{re.escape(section_name)}[ \t]*\n)[\s\S]*?(?=^##[ \t]+|\Z)"
    body = new_body.strip()
    new_block = lambda m: m.group(1) + body + "\n\n"
    new_md, n = re.subn(pattern, new_block, md or "", count=1, flags=re.MULTILINE)
    if n == 0:
        prefix = (md or "").rstrip("\n")
        return f"{prefix}\n\n## {section_name}\n{body}\n"
    return new_md


def _parse_numbered_answers(text):
    """Parse numbered answers in either format:

    Multi-line (canonical):
        1. foo
        2. bar baz
    Inline (user-pasted from mobile):
        1. foo 2. bar baz

    Returns {1: 'foo', 2: 'bar baz'}. Multi-line continuations are preserved.

    Safety: an `N. ` marker is only treated as a separator if N is strictly
    greater than the previous accepted marker — that way text like
    "step 1. then" inside an answer doesn't spuriously start a new entry.
    """
    import re
    if not text:
        return {}
    # Anchor each marker to start-of-string, after a newline, or after a space.
    pattern = re.compile(r"(?:^|(?<=\s))(\d+)\.\s+")
    raw = list(pattern.finditer(text))
    if not raw:
        return {}

    # Monotonic filter — drop matches where N is not strictly increasing.
    valid = [raw[0]]
    for m in raw[1:]:
        if int(m.group(1)) > int(valid[-1].group(1)):
            valid.append(m)

    answers = {}
    for i, m in enumerate(valid):
        n = int(m.group(1))
        start = m.end()
        end = valid[i + 1].start() if i + 1 < len(valid) else len(text)
        answers[n] = text[start:end].strip()
    return answers


def cmd_vision(arg, attachments=None):
    """Vision-doc commands: show / email / build / list / cancel.

    Special: `vision <slug>` with .md attached replaces the doc with the edited version.
    """
    parts = (arg or "").strip().split(None, 2)
    sub = parts[0].lower() if parts else "list"
    rest = parts[1].strip() if len(parts) > 1 else ""
    rest2 = parts[2].strip() if len(parts) > 2 else ""

    if sub == "list" or not sub:
        sessions = vision_list(limit=20)
        if not sessions:
            return "No vision sessions yet. Start one with `idea <your idea text>`."
        lines = ["**Vision sessions (most recent 20):**", ""]
        for s in sessions:
            kind = s.get("proposed_kind") or "—"
            status = s.get("status") or "?"
            built = f" → `{s['project_slug']}`" if s.get("project_slug") else ""
            lines.append(f"- `{s['slug']}` [{kind}] — {status}{built}")
        return "\n".join(lines)

    # `vision <slug>` with attached .md → user uploading their edited version
    if attachments and not rest:
        session = vision_get(sub)
        if session:
            return _vision_apply_attachment(session, attachments)

    if sub == "show" or sub == "view":
        return _vision_show(rest)
    if sub == "email":
        return _vision_email(rest)
    if sub == "questions":
        return _vision_questions(rest)
    if sub == "answer":
        return _vision_answer_one(rest, rest2)
    if sub == "answers":
        return _vision_answers_bulk(rest, rest2)
    if sub in ("review", "reviewanswers"):
        return _vision_review(rest)
    if sub == "build":
        return _vision_build(rest, kind_override=rest2 or None)
    if sub == "cancel":
        return _vision_cancel(rest)

    # Unknown sub — maybe it's actually a slug for show
    session = vision_get(sub)
    if session:
        return _vision_show(sub)

    return ("Usage:\n"
            "  `vision list` — list sessions\n"
            "  `vision show <slug>` — show a vision doc\n"
            "  `vision questions <slug>` — show just the open questions (mobile-friendly)\n"
            "  `vision answer <slug> <N> <text>` — answer one question in chat\n"
            "  `vision answers <slug> <text>` — replace all answers in one shot\n"
            "  `vision review <slug>` — Claude reviews your answers, suggests follow-ups\n"
            "  `vision email <slug>` — email the .md for laptop editing\n"
            "  `vision <slug>` (with .md attached) — replace the doc with your edited version\n"
            "  `vision build <slug> [kind]` — build a project from the doc\n"
            "  `vision cancel <slug>` — drop a session")


def _vision_show(slug):
    if not slug:
        return "Usage: `vision show <slug>`"
    session = vision_get(slug)
    if not session:
        return f"Vision `{slug}` not found. Try `vision list`."
    lines = [
        f"**Vision `{slug}`** — status: `{session.get('status', '?')}`",
        f"**Kind:** {session.get('proposed_kind') or '—'}",
        f"**Interpretation:** {session.get('interpretation') or '—'}",
        "",
        "---",
        "",
        session.get("vision_md") or "(no doc body)",
    ]
    return "\n".join(lines)


def _vision_email(slug):
    from bot.vision import send_vision_email
    if not slug:
        return "Usage: `vision email <slug>`"
    session = vision_get(slug)
    if not session:
        return f"Vision `{slug}` not found."
    title = _extract_title(session.get("vision_md")) or slug
    ok, info = send_vision_email(
        slug, title,
        session.get("raw_idea") or "",
        session.get("vision_md") or "",
    )
    if ok:
        vision_update(slug, status="emailed", mode="email")
        return (f"Emailed vision `{slug}` to **{info}**.\n"
                f"Edit the attached .md, then reply here with `vision {slug}` + the file.")
    return f"Email failed: {info}"


def _vision_cancel(slug):
    if not slug:
        return "Usage: `vision cancel <slug>`"
    session = vision_get(slug)
    if not session:
        return f"Vision `{slug}` not found."
    vision_update(slug, status="cancelled")
    return f"Vision `{slug}` cancelled."


def _vision_questions(slug):
    """Show just the Open Questions section + which ones are already answered."""
    if not slug:
        return "Usage: `vision questions <slug>`"
    session = vision_get(slug)
    if not session:
        return f"Vision `{slug}` not found."
    md = session.get("vision_md") or ""
    questions = _extract_section(md, "Open Questions")
    if not questions:
        return f"Vision `{slug}` has no `## Open Questions` section."

    answered = _parse_numbered_answers(_extract_section(md, "Your Answers") or "")
    lines = [f"**Open Questions for `{slug}`:**", "", questions, ""]
    if answered:
        nums = ", ".join(str(n) for n in sorted(answered))
        lines.append(f"_Answered so far: {nums}_")
        lines.append("")
    lines.extend([
        "Reply with:",
        f"- `vision answer {slug} <N> <text>` — answer one question",
        f"- `vision answers {slug} <text>` — replace all answers at once",
        f"- `vision build {slug}` — build now with whatever you've got",
    ])
    return "\n".join(lines)


def _vision_answer_one(slug, payload):
    """Record one numbered answer. payload = '<N> <answer text>'."""
    if not slug:
        return "Usage: `vision answer <slug> <N> <answer text>`"
    session = vision_get(slug)
    if not session:
        return f"Vision `{slug}` not found."
    parts = (payload or "").split(None, 1)
    if len(parts) < 2 or not parts[0].isdigit():
        return ("Usage: `vision answer <slug> <N> <answer text>`\n"
                "Example: `vision answer podcasttracker 1 episode level — show is too coarse`")
    qnum = int(parts[0])
    answer_text = parts[1].strip()

    md = session.get("vision_md") or ""
    answers = _parse_numbered_answers(_extract_section(md, "Your Answers") or "")
    answers[qnum] = answer_text

    new_body = "\n".join(f"{n}. {answers[n]}" for n in sorted(answers))
    new_md = _replace_section(md, "Your Answers", new_body)
    vision_update(slug, vision_md=new_md, status="received")
    return (f"Recorded answer {qnum} for `{slug}`. "
            f"{len(answers)} answered so far.\n"
            f"`vision questions {slug}` to see what's left, or `vision build {slug}` when ready.")


def _vision_answers_bulk(slug, text):
    """Replace the entire Your Answers section with free-form text.

    If the text parses as numbered answers (line- or space-separated), it's
    canonicalized to one per line. Otherwise stored verbatim.
    """
    if not slug:
        return "Usage: `vision answers <slug> <answer text>`"
    session = vision_get(slug)
    if not session:
        return f"Vision `{slug}` not found."
    if not text or not text.strip():
        return "Usage: `vision answers <slug> <answer text>` (provide the full block)"
    md = session.get("vision_md") or ""

    parsed = _parse_numbered_answers(text)
    if parsed:
        new_body = "\n".join(f"{n}. {parsed[n]}" for n in sorted(parsed))
        note = f"parsed {len(parsed)} numbered answer(s)"
    else:
        new_body = text.strip()
        note = f"{len(text)} chars (no numbered structure detected)"

    new_md = _replace_section(md, "Your Answers", new_body)
    vision_update(slug, vision_md=new_md, status="received")
    return f"Updated Your Answers for `{slug}` — {note}. Ready: `vision build {slug}`."


def _vision_review(slug):
    """Have Claude review the user's answers, classify them, suggest follow-ups."""
    from bot.vision import review_answers
    if not slug:
        return "Usage: `vision review <slug>`"
    session = vision_get(slug)
    if not session:
        return f"Vision `{slug}` not found."
    md = session.get("vision_md") or ""
    questions_text = _extract_section(md, "Open Questions")
    answers_text = _extract_section(md, "Your Answers")
    if not questions_text:
        return f"Vision `{slug}` has no `## Open Questions` to review against."
    if not answers_text:
        return (f"Vision `{slug}` has no answers yet. Use "
                f"`vision answer {slug} <N> <text>` first, then review.")

    try:
        result = review_answers(md)
    except Exception as e:
        return f"Couldn't review: {e}"

    status_icons = {
        "clear": "✅", "ambiguous": "⚠️", "asked_back": "❓", "missing": "❌",
    }
    question_map = _parse_numbered_answers(questions_text)

    lines = [
        f"**Review of `{slug}` answers**",
        "",
        f"**Verdict:** `{result['verdict']}` — {result['summary']}",
        "",
        "**Per-answer:**",
    ]
    for review in result.get("answer_reviews", []):
        n = review.get("question_number")
        status = review.get("status", "")
        icon = status_icons.get(status, "•")
        q_full = question_map.get(n, "")
        q_preview = q_full[:60] + ("…" if len(q_full) > 60 else "")
        lines.append(f"{icon} **{n}.** {q_preview}")
        comment = review.get("comment", "").strip()
        if comment:
            lines.append(f"   _{comment}_")

    # Auto-append follow-ups so they can be answered with normal numbering.
    followups = result.get("followup_questions") or []
    if followups:
        existing = _parse_numbered_answers(questions_text)
        next_n = (max(existing) if existing else 0) + 1
        new_q_lines = "\n".join(f"{next_n + i}. {q}" for i, q in enumerate(followups))
        appended = questions_text.rstrip() + "\n" + new_q_lines
        new_md = _replace_section(md, "Open Questions", appended)
        vision_update(slug, vision_md=new_md)
        last_n = next_n + len(followups) - 1
        lines.append("")
        lines.append(f"**Added {len(followups)} follow-up question(s) (Q{next_n}–Q{last_n}):**")
        for i, q in enumerate(followups):
            lines.append(f"{next_n + i}. {q}")
        lines.append("")
        lines.append(f"Answer with: `vision answer {slug} {next_n} <text>`")

    revised = result.get("revised_questions") or []
    if revised:
        lines.append("")
        lines.append("**Suggested question rewrite** (not applied — review and decide):")
        for i, q in enumerate(revised, 1):
            lines.append(f"{i}. {q}")
        lines.append("")
        lines.append(f"To apply, re-edit the doc via `vision email {slug}` "
                     f"or `vision answers {slug} <text>`.")

    if result.get("verdict") == "ready_to_build" and not followups:
        lines.append("")
        lines.append(f"All answers look clear. Run `vision build {slug}` when ready.")

    return "\n".join(lines)


def _vision_apply_attachment(session, attachments):
    """User uploaded an edited .md — replace vision_md and mark received."""
    slug = session["slug"]
    for att in attachments:
        filename = att.get("filename", "")
        content = att["content"]
        if isinstance(content, bytes):
            try:
                content = content.decode("utf-8")
            except UnicodeDecodeError:
                continue
        # Accept .md files or filenames containing 'vision'
        if not (filename.lower().endswith(".md") or "vision" in filename.lower()):
            continue
        vision_update(slug, vision_md=content, status="received")
        return (f"Got it — updated vision `{slug}` with your edits ({len(content)} chars).\n"
                f"Ready: `vision build {slug}` to queue the project.")
    return f"No .md attachment found on that message. Attach the edited vision-{slug}.md and resend."


def _vision_build(slug, kind_override=None):
    """Promote a vision session to an actual project."""
    if not slug:
        return "Usage: `vision build <slug> [story|studyws|app]`"
    session = vision_get(slug)
    if not session:
        return f"Vision `{slug}` not found."
    if session.get("status") == "built":
        return f"Vision `{slug}` was already built as `{session.get('project_slug')}`."

    kind = (kind_override or session.get("proposed_kind") or "unclear").lower()
    if kind == "unclear":
        return (f"Vision `{slug}` doesn't have a clear kind. Specify one:\n"
                f"`vision build {slug} story` (or `studyws` / `app`)")
    if kind not in ("story", "studyws", "app"):
        return f"Unknown kind `{kind}`. Use one of: story / studyws / app."

    vision_md = session.get("vision_md") or session.get("raw_idea") or ""
    title = _extract_title(vision_md) or slug

    try:
        if kind == "story":
            project_slug = _build_story_from_vision(slug, title, vision_md)
        elif kind == "studyws":
            project_slug = _build_studyws_from_vision(slug, title, vision_md)
        else:
            project_slug = _build_app_from_vision(slug, title, vision_md)
    except Exception as e:
        return f"Build failed for `{slug}`: {e}"

    vision_update(slug, status="built", project_slug=project_slug)
    return (f"Built **`{project_slug}`** from vision `{slug}` (kind: `{kind}`).\n"
            f"Queued — will start when a slot opens. Track with `status`.")


def _build_story_from_vision(vision_slug, title, vision_md):
    import json as _json
    import sqlite3 as _sqlite3
    base = _slug_from_idea(title) or _slug_from_idea(vision_slug) or "untitled"
    project_slug = f"story-{base}"
    if project_get(project_slug):
        project_slug = f"{project_slug}-{vision_slug[-6:]}"

    projects_dir = os.environ.get("NSAF_PROJECTS_DIR", "./projects")
    project_dir = os.path.join(projects_dir, project_slug)
    os.makedirs(project_dir, exist_ok=True)

    config = {
        "idea": f"Title: {title}\n\n{vision_md}",
        "scenes": "",
        "style": "",
        "notes": f"Generated from vision session {vision_slug}",
    }
    with open(os.path.join(project_dir, "story-config.json"), "w") as f:
        _json.dump(config, f, indent=2)
    with open(os.path.join(project_dir, "vision-source.md"), "w") as f:
        f.write(vision_md)

    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO projects (slug, project_dir, project_type, status) VALUES (?, ?, 'story', 'queued')",
            (project_slug, project_dir),
        )
        db.commit()
        pid = cursor.lastrowid
    except _sqlite3.IntegrityError as e:
        raise RuntimeError(f"Project insert failed: {e}")
    queue_enqueue(pid)
    return project_slug


def _build_studyws_from_vision(vision_slug, title, vision_md):
    import json as _json
    import re as _re
    import sqlite3 as _sqlite3
    base = _re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60] or "topic"
    project_slug = f"sws-{base}"
    if project_get(project_slug):
        project_slug = f"{project_slug}-{vision_slug[-6:]}"

    projects_dir = os.environ.get("NSAF_PROJECTS_DIR", "./projects")
    project_dir = os.path.join(projects_dir, project_slug)
    os.makedirs(project_dir, exist_ok=True)

    with open(os.path.join(project_dir, "source-material.md"), "w") as f:
        f.write(vision_md)
    config = {
        "topic": title,
        "chapters": 10,
        "level": "intermediate",
        "notes": f"Generated from vision session {vision_slug}",
        "source_url": "",
        "has_source_file": True,
    }
    with open(os.path.join(project_dir, "studyws-config.json"), "w") as f:
        _json.dump(config, f, indent=2)

    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO projects (slug, project_dir, project_type, status) VALUES (?, ?, 'studyws', 'queued')",
            (project_slug, project_dir),
        )
        db.commit()
        pid = cursor.lastrowid
    except _sqlite3.IntegrityError as e:
        raise RuntimeError(f"Project insert failed: {e}")
    queue_enqueue(pid)
    return project_slug


def _build_app_from_vision(vision_slug, title, vision_md):
    import re as _re
    import sqlite3 as _sqlite3
    db = get_db()
    today = date.today().isoformat()
    cursor = db.execute(
        """INSERT INTO ideas (date, source, rank, name, description, category, complexity,
               suggested_stack, temperature, tier)
           VALUES (?, 'vision', 99, ?, ?, 'uncategorized', 'medium', '{}', 0, 'vision')""",
        (today, title, vision_md[:2000]),
    )
    db.commit()
    idea_id = cursor.lastrowid

    base = _re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60] or "untitled"
    project_slug = base
    projects_dir = os.environ.get("NSAF_PROJECTS_DIR", "./projects")
    project_dir = os.path.join(projects_dir, project_slug)
    try:
        pid = project_create(project_slug, idea_id, project_dir)
    except _sqlite3.IntegrityError:
        project_slug = f"{project_slug}-{vision_slug[-6:]}"
        project_dir = os.path.join(projects_dir, project_slug)
        pid = project_create(project_slug, idea_id, project_dir)

    os.makedirs(project_dir, exist_ok=True)
    with open(os.path.join(project_dir, "vision.md"), "w") as f:
        f.write(vision_md)

    queue_enqueue(pid)
    return project_slug


def cmd_idea_detail(arg):
    """Show details for an idea. Supports: 'idea <id>', 'idea story <id>', 'idea study <id>'."""
    kind, rest = _parse_kind_args(arg)
    if kind == "story":
        return _kind_idea_detail(rest, kind="story")
    if kind == "study":
        return _kind_idea_detail(rest, kind="study")

    if not arg:
        return "Usage: `idea <id>` or `idea story <id>` or `idea study <id>`"
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


def _kind_idea_detail(rest, *, kind):
    if not rest:
        return f"Usage: `idea {kind} <id>`"
    try:
        idea_id = int(rest)
    except ValueError:
        return f"Invalid {kind} idea ID: `{rest}`"

    if kind == "story":
        idea = story_idea_get(idea_id)
        link_col = "story_idea_id"
    else:
        idea = study_idea_get(idea_id)
        link_col = "study_idea_id"

    if not idea:
        return f"{kind.capitalize()} idea #{idea_id} not found."

    ensure_project_idea_link_columns()
    db = get_db()
    project = db.execute(
        f"SELECT slug, status, deployed_url, sdd_phase, sdd_active_role, sdd_progress "
        f"FROM projects WHERE {link_col} = ?",
        (idea_id,),
    ).fetchone()

    lines = [f"**{kind.capitalize()} Idea #{idea_id}: {idea['name']}**\n"]
    lines.append(f"**Description:** {idea['description']}")
    lines.append(f"**Source:** {idea['source']}  (tier: {idea.get('tier') or '—'})")
    lines.append(f"**Generated:** {idea['date']}")

    if kind == "story":
        if idea.get("target_age"):
            lines.append(f"**Target age:** {idea['target_age']}")
        if idea.get("length_minutes"):
            lines.append(f"**Length:** {idea['length_minutes']} min")
        if idea.get("art_style_hint"):
            lines.append(f"**Art style hint:** {idea['art_style_hint']}")
        themes = idea.get("themes")
        if themes:
            try:
                parsed = json.loads(themes) if isinstance(themes, str) else themes
                if isinstance(parsed, list):
                    themes = ", ".join(parsed)
            except (json.JSONDecodeError, TypeError):
                pass
            lines.append(f"**Themes:** {themes}")
    else:
        if idea.get("level"):
            lines.append(f"**Level:** {idea['level']}")
        if idea.get("chapters"):
            lines.append(f"**Chapters:** {idea['chapters']}")
        if idea.get("suggested_source_url"):
            lines.append(f"**Source URL:** {idea['suggested_source_url']}")

    if project:
        lines.append(f"\n**Build Status:** `{project['status']}`")
        lines.append(f"**Project:** `{project['slug']}`")
        if project["deployed_url"]:
            lines.append(f"**Local URL:** {project['deployed_url']}")
    else:
        lines.append(f"\n**Build Status:** not queued")
        lines.append(f"Use `queue {kind} {idea_id}` to add to build queue.")

    return "\n".join(lines)


def _slugify(name):
    """Convert app name to a URL-safe slug."""
    import re
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")[:60]


def _projects_root():
    """Canonical absolute path of the projects directory."""
    return os.path.realpath(os.environ.get("NSAF_PROJECTS_DIR", "./projects"))


def _safe_project_dir(project_dir):
    """Return the canonical project_dir only if it lives strictly inside the
    projects root. Returns None otherwise — used as a guard before any
    destructive filesystem operation on a path that came from the DB.
    """
    if not project_dir:
        return None
    try:
        resolved = os.path.realpath(project_dir)
    except (OSError, ValueError):
        return None
    root = _projects_root()
    try:
        if os.path.commonpath([resolved, root]) != root:
            return None
    except ValueError:
        # Paths on different drives or otherwise incomparable
        return None
    if resolved == root:
        # Never wipe the root itself
        return None
    return resolved


def cmd_queue_idea(arg):
    """Add an idea to the build queue. Supports: 'queue <id>', 'queue story <id>', 'queue study <id>'."""
    kind, rest = _parse_kind_args(arg)
    if kind == "story":
        return _queue_story_idea(rest)
    if kind == "study":
        return _queue_study_idea(rest)

    if not arg:
        return "Usage: `queue <idea-id>` or `queue story <id>` or `queue study <id>`"
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


def _queue_story_idea(rest):
    """Materialize a story_ideas row into a story project and enqueue it."""
    if not rest:
        return "Usage: `queue story <id>`"
    try:
        idea_id = int(rest)
    except ValueError:
        return f"Invalid story idea ID: `{rest}`"

    idea = story_idea_get(idea_id)
    if not idea:
        return f"Story idea #{idea_id} not found."

    ensure_project_idea_link_columns()
    db = get_db()
    existing = db.execute(
        "SELECT slug, status FROM projects WHERE story_idea_id = ?", (idea_id,)
    ).fetchone()
    if existing:
        return f"Story idea #{idea_id} already has project `{existing['slug']}` ({existing['status']})."

    slug_base = _slug_from_idea(idea["name"]) or _slugify(idea["name"])
    slug = f"story-{slug_base}"
    if project_get(slug):
        slug = f"{slug}-{idea_id}"

    projects_dir = os.environ.get("NSAF_PROJECTS_DIR", "./projects")
    project_dir = os.path.join(projects_dir, slug)
    os.makedirs(project_dir, exist_ok=True)

    import json as _json
    config = {
        "idea": idea["description"],
        "scenes": "",
        "style": idea.get("art_style_hint") or "",
        "notes": f"target_age={idea.get('target_age') or ''}; length_minutes={idea.get('length_minutes') or ''}".strip("; "),
    }
    with open(os.path.join(project_dir, "story-config.json"), "w") as f:
        _json.dump(config, f, indent=2)

    import sqlite3
    try:
        cursor = db.execute(
            "INSERT INTO projects (slug, project_dir, project_type, status, story_idea_id) "
            "VALUES (?, ?, 'story', 'queued', ?)",
            (slug, project_dir, idea_id),
        )
        db.commit()
        pid = cursor.lastrowid
    except sqlite3.IntegrityError:
        return f"Project `{slug}` already exists."

    queue_enqueue(pid)
    return (
        f"Story idea #{idea_id} (**{idea['name']}**) queued as `{slug}`. "
        f"Pipeline: concept → outline → script → illustrations → narration → MP4. "
        f"Fetch with `fetchstory {slug}` when complete."
    )


def _queue_study_idea(rest):
    """Materialize a study_ideas row into a studyws project and enqueue it."""
    if not rest:
        return "Usage: `queue study <id>`"
    try:
        idea_id = int(rest)
    except ValueError:
        return f"Invalid study idea ID: `{rest}`"

    idea = study_idea_get(idea_id)
    if not idea:
        return f"Study idea #{idea_id} not found."

    ensure_project_idea_link_columns()
    db = get_db()
    existing = db.execute(
        "SELECT slug, status FROM projects WHERE study_idea_id = ?", (idea_id,)
    ).fetchone()
    if existing:
        return f"Study idea #{idea_id} already has project `{existing['slug']}` ({existing['status']})."

    import re
    slug_base = re.sub(r'[^a-z0-9]+', '-', idea["name"].lower()).strip('-')[:60]
    slug = f"sws-{slug_base}"
    if project_get(slug):
        slug = f"{slug}-{idea_id}"

    projects_dir = os.environ.get("NSAF_PROJECTS_DIR", "./projects")
    project_dir = os.path.join(projects_dir, slug)
    os.makedirs(project_dir, exist_ok=True)

    chapters = idea.get("chapters") or 12
    level = (idea.get("level") or "intermediate").lower()
    source_url = idea.get("suggested_source_url") or ""

    import json as _json
    config = {
        "topic": idea["name"],
        "chapters": chapters,
        "level": level,
        "notes": idea.get("description") or "",
        "source_url": source_url,
        "has_source_file": False,
    }
    with open(os.path.join(project_dir, "studyws-config.json"), "w") as f:
        _json.dump(config, f, indent=2)

    import sqlite3
    try:
        cursor = db.execute(
            "INSERT INTO projects (slug, project_dir, project_type, status, study_idea_id) "
            "VALUES (?, ?, 'studyws', 'queued', ?)",
            (slug, project_dir, idea_id),
        )
        db.commit()
        pid = cursor.lastrowid
    except sqlite3.IntegrityError:
        return f"Project `{slug}` already exists."

    queue_enqueue(pid)
    summary = [
        f"Study idea #{idea_id} (**{idea['name']}**) queued as `{slug}`.",
        f"**Chapters:** {chapters}  **Level:** {level}",
    ]
    if source_url:
        summary.append(f"**Source:** {source_url}")
    summary.append("Will produce: textbook, study guides, slide descriptions, podcast prompt.")
    return "\n".join(summary)


_GENERATE_KINDS = {
    "stories": {
        "script": "generate_stories.py",
        "label": "Story idea",
        "follow_up": "`stories`",
    },
    "studies": {
        "script": "generate_studies.py",
        "label": "Study idea",
        "follow_up": "`studies`",
    },
}


def cmd_generate(arg):
    """Trigger idea generation. Subcommands: '' (apps), 'stories [N]', 'studies [N]'."""
    nsaf_dir = os.environ.get("NSAF_DIR", os.path.join(os.path.dirname(__file__), "..", ".."))
    venv_python = os.path.join(nsaf_dir, "venv", "bin", "python")

    parts = (arg or "").strip().split()
    sub = parts[0].lower() if parts else ""
    count = None
    if len(parts) > 1:
        try:
            count = int(parts[1])
        except ValueError:
            return f"Invalid count: `{parts[1]}`. Usage: `generate {sub} [count]`"

    if sub == "":
        script_name = "generate.py"
        label = "Idea"
        follow_up = "`ideas`"
        cmd = [venv_python, os.path.join(nsaf_dir, "idea-generator", script_name)]
    elif sub in _GENERATE_KINDS:
        meta = _GENERATE_KINDS[sub]
        script_name = meta["script"]
        label = meta["label"]
        follow_up = meta["follow_up"]
        cmd = [venv_python, os.path.join(nsaf_dir, "idea-generator", script_name)]
        if count is not None:
            cmd.extend(["--count", str(count)])
    else:
        valid = ", ".join(["(empty)"] + list(_GENERATE_KINDS.keys()))
        return f"Unknown generate subcommand: `{sub}`. Valid: {valid}"

    script = cmd[1]
    if not os.path.exists(script):
        return f"Generator script not found at `{script}`"

    try:
        result = subprocess.Popen(
            cmd,
            cwd=nsaf_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        count_note = f" (count={count})" if count is not None else ""
        return f"{label} generation started (PID {result.pid}){count_note}. Check back in a minute with {follow_up}."
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


def _export_ideas_csv(out_path):
    """Write the apps idea export CSV. Returns (path, row_count, summary)."""
    import csv
    import io

    db = get_db()
    db.execute("""
        UPDATE projects SET sdd_phase = 'complete', sdd_progress = 100
        WHERE status IN ('deployed-local', 'promoted', 'archived') AND sdd_phase IS NOT NULL AND sdd_phase != 'complete'
    """)
    db.commit()

    rows = db.execute("""
        SELECT
            i.id as idea_id, i.date, i.source, i.name, i.description,
            i.category, i.complexity, i.suggested_stack,
            COALESCE(i.temperature, 0) as temperature,
            COALESCE(i.tier, '') as tier,
            p.id as project_id, p.slug, p.status, p.port_start,
            p.deployed_url, p.render_url, p.sdd_phase, p.sdd_progress,
            p.started_at, p.completed_at
        FROM ideas i
        LEFT JOIN projects p ON p.idea_id = i.id
        ORDER BY i.date DESC, i.source, i.temperature
    """).fetchall()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "idea_id", "date", "source", "temperature", "tier", "name", "description",
        "category", "complexity", "suggested_stack",
        "project_slug", "build_status", "port", "local_url", "render_url",
        "phase", "progress", "started", "completed",
    ])
    for r in rows:
        status = r["status"] or "not queued"
        phase = r["sdd_phase"] or ""
        progress = r["sdd_progress"] or 0
        if status in ("deployed-local", "promoted", "archived"):
            phase = "complete"
            progress = 100
        writer.writerow([
            r["idea_id"], r["date"], r["source"],
            r["temperature"], r["tier"],
            r["name"], r["description"], r["category"], r["complexity"],
            r["suggested_stack"] or "",
            r["slug"] or "", status, r["port_start"] or "",
            r["deployed_url"] or "", r["render_url"] or "",
            phase, progress,
            r["started_at"] or "", r["completed_at"] or "",
        ])

    with open(out_path, "w") as f:
        f.write(buf.getvalue())

    queued_count = sum(1 for r in rows if r["status"])
    unqueued_count = sum(1 for r in rows if not r["status"])
    summary = f"{len(rows)} ideas ({queued_count} built/queued, {unqueued_count} not queued)"
    return out_path, len(rows), summary


def _export_stories_csv(out_path):
    """Write the story idea export CSV. Returns (path, row_count, summary)."""
    import csv
    import io

    db = get_db()
    table_exists = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='story_ideas'"
    ).fetchone()
    rows = db.execute("""
        SELECT id as idea_id, date, source,
               COALESCE(temperature, 0) as temperature,
               COALESCE(tier, '') as tier,
               name, description, target_age, length_minutes, art_style_hint, themes
        FROM story_ideas
        ORDER BY date DESC, source, temperature
    """).fetchall() if table_exists else []

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "idea_id", "date", "source", "temperature", "tier",
        "name", "description", "target_age", "length_minutes",
        "art_style_hint", "themes",
    ])
    for r in rows:
        writer.writerow([
            r["idea_id"], r["date"], r["source"],
            r["temperature"], r["tier"],
            r["name"], r["description"],
            r["target_age"] or "", r["length_minutes"] or "",
            r["art_style_hint"] or "", r["themes"] or "",
        ])

    with open(out_path, "w") as f:
        f.write(buf.getvalue())

    return out_path, len(rows), f"{len(rows)} story ideas"


def _export_studies_csv(out_path):
    """Write the study idea export CSV. Returns (path, row_count, summary)."""
    import csv
    import io

    db = get_db()
    table_exists = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='study_ideas'"
    ).fetchone()
    rows = db.execute("""
        SELECT id as idea_id, date, source,
               COALESCE(temperature, 0) as temperature,
               COALESCE(tier, '') as tier,
               name, description, level, chapters, suggested_source_url
        FROM study_ideas
        ORDER BY date DESC, source, temperature
    """).fetchall() if table_exists else []

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "idea_id", "date", "source", "temperature", "tier",
        "name", "description", "level", "chapters", "suggested_source_url",
    ])
    for r in rows:
        writer.writerow([
            r["idea_id"], r["date"], r["source"],
            r["temperature"], r["tier"],
            r["name"], r["description"],
            r["level"] or "", r["chapters"] or "",
            r["suggested_source_url"] or "",
        ])

    with open(out_path, "w") as f:
        f.write(buf.getvalue())

    return out_path, len(rows), f"{len(rows)} study ideas"


def cmd_export(arg):
    """Export ideas as CSV. Subcommands: '' (ideas), 'ideas', 'stories', 'studies', 'all'."""
    import tempfile
    import zipfile

    sub = (arg or "").strip().lower()
    tmp = tempfile.gettempdir()

    if sub in ("", "ideas"):
        path, _, summary = _export_ideas_csv(os.path.join(tmp, "nsaf-export.csv"))
        return {"text": f"**Nightshift AutoFoundry Export** — {summary}", "files": [path]}

    if sub == "stories":
        path, _, summary = _export_stories_csv(os.path.join(tmp, "nsaf-export-stories.csv"))
        return {"text": f"**Story Idea Export** — {summary}", "files": [path]}

    if sub == "studies":
        path, _, summary = _export_studies_csv(os.path.join(tmp, "nsaf-export-studies.csv"))
        return {"text": f"**Study Idea Export** — {summary}", "files": [path]}

    if sub == "all":
        ideas_path, n_ideas, ideas_sum = _export_ideas_csv(os.path.join(tmp, "nsaf-export-ideas.csv"))
        stories_path, n_stories, stories_sum = _export_stories_csv(os.path.join(tmp, "nsaf-export-stories.csv"))
        studies_path, n_studies, studies_sum = _export_studies_csv(os.path.join(tmp, "nsaf-export-studies.csv"))
        zip_path = os.path.join(tmp, "nsaf-export-all.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(ideas_path, "nsaf-export-ideas.csv")
            zf.write(stories_path, "nsaf-export-stories.csv")
            zf.write(studies_path, "nsaf-export-studies.csv")
        return {
            "text": (
                f"**NSAF Full Export** — {ideas_sum}; {stories_sum}; {studies_sum}"
            ),
            "files": [zip_path],
        }

    return f"Unknown export target: `{sub}`. Valid: ideas, stories, studies, all"


def cmd_delete(arg):
    """Delete one or more projects by ID or slug."""
    if not arg:
        return "Usage: `delete <id-or-slug> [id-or-slug ...]`"

    targets = arg.split()
    deleted = []
    errors = []

    for target in targets:
        # Find by ID or slug
        db = get_db()
        project = None
        try:
            pid = int(target)
            row = db.execute("SELECT * FROM projects WHERE id = ?", (pid,)).fetchone()
            if row:
                project = dict(row)
        except ValueError:
            project = project_get(target)

        if not project:
            errors.append(f"`{target}` not found")
            continue

        slug = project["slug"]

        # Kill any running processes on the project's ports
        if project.get("port_start"):
            try:
                subprocess.run(["fuser", "-k", f"{project['port_start']}/tcp"], capture_output=True, timeout=5)
            except Exception:
                pass

        # Remove project directory — but only if it lives under NSAF_PROJECTS_DIR.
        # A malformed DB row pointing at, say, /home/smahoney must not be wiped.
        project_dir = project.get("project_dir", "")
        safe_dir = _safe_project_dir(project_dir)
        if project_dir and not safe_dir:
            errors.append(
                f"`{target}` — refusing to delete `{project_dir}` "
                f"(outside `{_projects_root()}`). Fix the DB row or remove the path manually."
            )
            continue
        if safe_dir and os.path.isdir(safe_dir):
            import shutil
            shutil.rmtree(safe_dir, ignore_errors=True)

        # Clean up DB
        db.execute("DELETE FROM queue WHERE project_id = ?", (project["id"],))
        db.execute("DELETE FROM ports WHERE project_id = ?", (project["id"],))
        db.execute("DELETE FROM projects WHERE id = ?", (project["id"],))
        db.commit()

        deleted.append(slug)

    lines = []
    if deleted:
        lines.append(f"Deleted: {', '.join(f'`{s}`' for s in deleted)}")
    if errors:
        lines.append(f"Not found: {', '.join(errors)}")
    return "\n".join(lines)


def cmd_rebuild(arg):
    """Rebuild a project from scratch with optional notes."""
    if not arg:
        return "Usage: `rebuild <slug> [notes about what to change]`"

    parts = arg.split(None, 1)
    slug = parts[0]
    notes = parts[1] if len(parts) > 1 else ""

    project = project_get(slug)
    if not project:
        return f"Project `{slug}` not found."

    project_dir = project.get("project_dir", "")

    # Kill running processes
    if project.get("port_start"):
        try:
            subprocess.run(["fuser", "-k", f"{project['port_start']}/tcp"], capture_output=True, timeout=5)
        except Exception:
            pass

    # Remove old project directory — but only if it lives under NSAF_PROJECTS_DIR.
    safe_dir = _safe_project_dir(project_dir)
    if project_dir and not safe_dir:
        return (
            f"Project `{slug}` has `project_dir` set to `{project_dir}` "
            f"which is outside `{_projects_root()}`. Refusing to rebuild — "
            f"fix the DB row first."
        )
    if safe_dir and os.path.isdir(safe_dir):
        import shutil
        shutil.rmtree(safe_dir, ignore_errors=True)

    # Save rebuild notes to DB and re-queue
    rebuild_note = f"REBUILD: {notes}" if notes else "REBUILD from scratch"
    project_update(slug,
        status="queued",
        port_start=None, port_end=None,
        started_at=None, completed_at=None,
        stall_alerted=0, sdd_phase=None,
        sdd_active_role=None, sdd_progress=0,
        deployed_url=None, render_url=None,
    )

    # Release ports
    db = get_db()
    db.execute("DELETE FROM ports WHERE project_id = ?", (project["id"],))
    db.execute("DELETE FROM queue WHERE project_id = ?", (project["id"],))
    db.commit()
    queue_enqueue(project["id"])

    # Write rebuild notes so the scaffolder can include them in the vision doc
    notes_dir = os.path.join(os.environ.get("NSAF_PROJECTS_DIR", "./projects"), slug)
    os.makedirs(notes_dir, exist_ok=True)
    if notes:
        with open(os.path.join(notes_dir, "rebuild-notes.md"), "w") as f:
            f.write(f"# Rebuild Notes\n\n{notes}\n")

    return f"Project `{slug}` queued for complete rebuild.\n**Notes:** {notes or 'none'}"


def cmd_modify(arg):
    """Spawn a Claude session to modify an existing project."""
    if not arg:
        return "Usage: `modify <slug> <description of changes needed>`"

    parts = arg.split(None, 1)
    slug = parts[0]
    changes = parts[1] if len(parts) > 1 else "Make improvements to this project."

    project = project_get(slug)
    if not project:
        return f"Project `{slug}` not found."

    project_dir = project.get("project_dir", "")
    if not project_dir or not os.path.isdir(project_dir):
        return f"Project directory for `{slug}` not found."

    prompt = (
        f"You are modifying an existing deployed web app at {project_dir}. "
        f"The app is currently running at {project.get('deployed_url', 'unknown')}. "
        f"\n\nCHANGES REQUESTED: {changes}"
        f"\n\nMake the requested changes, test them, and restart the app. "
        f"Do NOT rebuild from scratch — modify the existing code. "
        f"Keep everything that works, only change what's needed."
    )

    claude_bin = os.environ.get("NSAF_CLAUDE_COMMAND", "claude").split()[0]
    modify_log = os.path.join(project_dir, "modify.log")

    try:
        proc = subprocess.Popen(
            [claude_bin, "-p", prompt, "--dangerously-skip-permissions"],
            cwd=project_dir,
            stdout=open(modify_log, "w"),
            stderr=subprocess.STDOUT,
        )
        return (
            f"Modify session started for `{slug}` (PID {proc.pid}).\n\n"
            f"**Changes:** {changes}\n"
            f"**Log:** `{modify_log}`"
        )
    except Exception as e:
        return f"Failed to start modify session: {e}"


def cmd_demote(slug):
    """Remove from Coolify + Cloudflare (revert to local-only)."""
    if not slug:
        return "Usage: `demote <slug>`"

    project = project_get(slug)
    if not project:
        return f"Project `{slug}` not found."

    if project["status"] != "promoted":
        return f"Project `{slug}` is `{project['status']}` — can only demote promoted projects."

    coolify_url = os.environ.get("COOLIFY_API_URL", "")
    coolify_token = os.environ.get("COOLIFY_API_TOKEN", "")
    domain = os.environ.get("NSAF_DOMAIN", "seanmahoney.ai")

    import requests as req

    lines = [f"**Demoting `{slug}`**\n"]

    # Remove from Coolify
    try:
        resp = req.get(
            f"{coolify_url}/api/v1/applications",
            headers={"Authorization": f"Bearer {coolify_token}"},
            timeout=15,
        )
        resp.raise_for_status()
        apps = resp.json()
        coolify_app = next((a for a in apps if a.get("name") == slug), None)

        if coolify_app:
            req.delete(
                f"{coolify_url}/api/v1/applications/{coolify_app['uuid']}",
                headers={"Authorization": f"Bearer {coolify_token}"},
                timeout=15,
            )
            lines.append("1. Coolify: app removed")
        else:
            lines.append("1. Coolify: app not found (already removed?)")
    except Exception as e:
        lines.append(f"1. Coolify cleanup failed: {e}")

    # Remove Cloudflare tunnel route + DNS
    hostname = f"{slug}.{domain}"
    try:
        _remove_cloudflare_tunnel_route(hostname)
        lines.append("2. Cloudflare: tunnel route + DNS removed")
    except Exception as e:
        lines.append(f"2. Cloudflare cleanup failed: {e}")

    project_update(slug, status="deployed-local", render_url=None)
    lines.append("3. Status: reverted to local-only")

    return "\n".join(lines)


def cmd_archive(slug):
    """Stop a project from running locally but keep the files."""
    if not slug:
        return "Usage: `archive <slug>`"

    project = project_get(slug)
    if not project:
        return f"Project `{slug}` not found."

    # Kill running processes on project ports
    if project.get("port_start"):
        for port in range(project["port_start"], project.get("port_end", project["port_start"]) + 1):
            try:
                subprocess.run(["fuser", "-k", f"{port}/tcp"], capture_output=True, timeout=5)
            except Exception:
                pass

    # Release ports
    db = get_db()
    db.execute("DELETE FROM ports WHERE project_id = ?", (project["id"],))
    db.commit()

    project_update(slug, status="archived", port_start=None, port_end=None, deployed_url=None)
    return f"Project `{slug}` archived. Processes stopped, ports released. Files preserved at `{project.get('project_dir', '?')}`."


def cmd_sws(arg, attachments=None):
    """Generate a StudyWS learning package for a topic."""
    if not arg:
        return "Usage: `sws <topic> [options]`\nExample: `sws Kubernetes Networking`\nExample: `sws Machine Learning --chapters 12 --level beginner`"

    # Parse topic and optional flags
    import re
    chapters = 10
    level = "intermediate"
    notes = ""
    source_url = ""

    # Extract URLs from the argument
    url_match = re.search(r'(https?://\S+)', arg)
    if url_match:
        source_url = url_match.group(1)
        arg = arg[:url_match.start()] + arg[url_match.end():]

    # Extract --chapters N
    ch_match = re.search(r'--chapters\s+(\d+)', arg)
    if ch_match:
        chapters = int(ch_match.group(1))
        arg = arg[:ch_match.start()] + arg[ch_match.end():]

    # Extract --level <level>
    lv_match = re.search(r'--level\s+(\w+)', arg)
    if lv_match:
        level = lv_match.group(1)
        arg = arg[:lv_match.start()] + arg[lv_match.end():]

    # Handle shorthand --beginner, --intermediate, --advanced
    for lv in ["beginner", "intermediate", "advanced"]:
        lv_short = re.search(rf'--{lv}\b', arg, re.IGNORECASE)
        if lv_short:
            level = lv
            arg = arg[:lv_short.start()] + arg[lv_short.end():]
            break

    # Extract --notes "..."
    nt_match = re.search(r'--notes\s+"([^"]+)"', arg)
    if not nt_match:
        nt_match = re.search(r'--notes\s+(\S+)', arg)
    if nt_match:
        notes = nt_match.group(1)
        arg = arg[:nt_match.start()] + arg[nt_match.end():]

    topic = arg.strip()

    # If only a URL was provided, derive topic from the URL
    if not topic and source_url:
        # Extract filename or path as topic hint
        from urllib.parse import urlparse
        path = urlparse(source_url).path
        filename = path.split('/')[-1].replace('.pdf', '').replace('.html', '').replace('_', ' ').replace('-', ' ')
        topic = filename if filename else "Study Material"

    if not topic:
        return "Please provide a topic or URL. Example: `sws Kubernetes Networking` or `sws https://example.com/syllabus.pdf`"

    # Create slug from topic
    slug = re.sub(r'[^a-z0-9]+', '-', topic.lower()).strip('-')[:60]
    slug = f"sws-{slug}"

    projects_dir = os.environ.get("NSAF_PROJECTS_DIR", "./projects")
    project_dir = os.path.join(projects_dir, slug)

    # Check if already exists
    existing = project_get(slug)
    if existing:
        return f"StudyWS project `{slug}` already exists ({existing['status']}). Use `rebuild {slug}` to regenerate."

    # Create project directory and config
    os.makedirs(project_dir, exist_ok=True)

    # Save file attachments as source material
    has_source_file = False
    if attachments:
        for att in attachments:
            content = att["content"]
            ct = att.get("content_type", "")
            # Decode text-based attachments to string
            if isinstance(content, bytes):
                if ct.startswith("text/") or ct in ("application/json", "application/xml"):
                    content = content.decode("utf-8", errors="replace")
                elif ct == "application/pdf":
                    # Save PDF as-is for Claude to read
                    pdf_path = os.path.join(project_dir, "source-material.pdf")
                    with open(pdf_path, "wb") as f:
                        f.write(content)
                    has_source_file = True
                    continue
                else:
                    # Try to decode as text
                    try:
                        content = content.decode("utf-8")
                    except UnicodeDecodeError:
                        continue
            with open(os.path.join(project_dir, "source-material.md"), "w") as f:
                f.write(content)
            has_source_file = True

    import json as _json
    config = {
        "topic": topic,
        "chapters": chapters,
        "level": level,
        "notes": notes,
        "source_url": source_url,
        "has_source_file": has_source_file,
    }
    with open(os.path.join(project_dir, "studyws-config.json"), "w") as f:
        _json.dump(config, f, indent=2)

    # Create project in DB with type=studyws
    import sqlite3
    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO projects (slug, project_dir, project_type, status) VALUES (?, ?, 'studyws', 'queued')",
            (slug, project_dir),
        )
        db.commit()
        pid = cursor.lastrowid
    except sqlite3.IntegrityError:
        return f"Project `{slug}` already exists."

    queue_enqueue(pid)

    lines = [
        f"**StudyWS project queued: `{slug}`**\n",
        f"**Topic:** {topic}",
        f"**Chapters:** {chapters}",
        f"**Level:** {level}",
    ]
    if has_source_file:
        lines.append(f"**Source:** attached file saved as source material")
    elif source_url:
        lines.append(f"**Source:** {source_url}")
    if notes:
        lines.append(f"**Notes:** {notes}")
    lines.append(f"\nWill produce: textbook, interactive study guides, slide descriptions, podcast prompt.")
    lines.append(f"Building will start when a slot opens.")

    return "\n".join(lines)


_STORY_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "of", "to", "in", "on", "at",
    "by", "for", "with", "from", "as", "is", "are", "was", "were",
    "be", "been", "being", "that", "this", "these", "those", "it", "its",
    "his", "her", "their", "our", "my", "your", "he", "she", "they", "we",
    "who", "whom", "which", "what", "when", "where", "why", "how",
    "about", "all", "any", "some", "no", "not", "so", "too", "very",
    "up", "out", "off", "over", "than", "then", "just", "also",
}


def _slug_from_idea(idea):
    """Extract a short memorable slug from the first few non-stopwords of the idea."""
    import re
    words = re.findall(r"[a-z0-9]+", idea.lower())
    meaningful = [w for w in words if w not in _STORY_STOPWORDS and len(w) > 2]
    if not meaningful:
        meaningful = words
    return "-".join(meaningful[:4])[:40].rstrip("-") or "untitled"


def _extract_flag(arg, name):
    """Pull `--<name> <value>` out of arg. Accepts quoted or multi-word unquoted
    values (reads until next --flag or end-of-string). Returns (value, remaining_arg)."""
    import re
    # Quoted form first: --flag "value with spaces"
    m = re.search(rf'--{name}\s+"([^"]+)"', arg)
    if not m:
        # Unquoted form: --flag value words until next --flag or end
        m = re.search(rf'--{name}\s+(.+?)(?=\s+--\w|\s*$)', arg)
    if not m:
        return "", arg
    return m.group(1).strip(), (arg[:m.start()] + arg[m.end():]).strip()


def cmd_story(arg):
    """Generate an illustrated audio story from an idea."""
    if not arg:
        return ("Usage: `story <idea>` or `story --title <title> --idea \"<idea>\"`\n"
                "Example: `story A bear cub afraid of the dark learns to love the night sky`\n"
                "Example: `story --title Kind Boy --idea \"A girl shows kindness to an angry boy\"`\n"
                "Options: `--scenes 8`, `--style \"watercolor storybook\"`, `--notes \"bedtime tone\"`")

    import re
    import time

    title, arg = _extract_flag(arg, "title")
    idea_flag, arg = _extract_flag(arg, "idea")
    style, arg = _extract_flag(arg, "style")
    notes, arg = _extract_flag(arg, "notes")
    scenes, arg = _extract_flag(arg, "scenes")
    scenes = scenes if scenes.isdigit() else ""

    # --idea wins; fall back to whatever positional text is left
    idea = idea_flag.strip() if idea_flag else arg.strip()
    if not idea:
        return "Please provide a story idea. Example: `story A clever fox outsmarts a bridge troll`"

    # Slug: explicit --title wins; otherwise extract meaningful words from idea
    if title:
        slug_base = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')[:40]
    else:
        slug_base = _slug_from_idea(idea)
    slug = f"story-{slug_base}"

    # If slug already exists (e.g. collision), append a short timestamp suffix
    if project_get(slug):
        slug = f"{slug}-{int(time.time()) % 10000}"

    projects_dir = os.environ.get("NSAF_PROJECTS_DIR", "./projects")
    project_dir = os.path.join(projects_dir, slug)

    os.makedirs(project_dir, exist_ok=True)

    import json as _json
    config = {
        "idea": idea,
        "scenes": scenes,
        "style": style,
        "notes": notes,
    }
    with open(os.path.join(project_dir, "story-config.json"), "w") as f:
        _json.dump(config, f, indent=2)

    import sqlite3
    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO projects (slug, project_dir, project_type, status) VALUES (?, ?, 'story', 'queued')",
            (slug, project_dir),
        )
        db.commit()
        pid = cursor.lastrowid
    except sqlite3.IntegrityError:
        return f"Project `{slug}` already exists — pass a different `--title` to avoid the collision."

    queue_enqueue(pid)

    lines = [
        f"**Story project queued: `{slug}`**\n",
        f"**Idea:** {idea}",
    ]
    if scenes:
        lines.append(f"**Scenes:** {scenes}")
    if style:
        lines.append(f"**Style:** {style}")
    if notes:
        lines.append(f"**Notes:** {notes}")
    lines.append("\nPipeline: concept → outline → script → illustrations → narration → MP4.")
    lines.append("When complete, fetch the video with `fetchstory " + slug + "`.")
    lines.append("Building will start when a slot opens.")

    return "\n".join(lines)


def cmd_fetchstory(arg):
    """Return the final.mp4 for a completed story project as a Webex attachment."""
    slug = arg.strip()
    if not slug:
        return "Usage: `fetchstory <slug>`"

    project = project_get(slug)
    if not project:
        return f"No project found with slug `{slug}`."

    if (project.get("project_type") or "app") != "story":
        return f"`{slug}` is not a story project."

    final_mp4 = os.path.join(project["project_dir"], "story-output", "final.mp4")
    if not os.path.exists(final_mp4):
        return f"No final.mp4 yet for `{slug}` (status: {project['status']})."

    # Webex attachment limit is ~100MB
    size = os.path.getsize(final_mp4)
    mb = size / (1024 * 1024)
    if size > 95 * 1024 * 1024:
        return (f"**{slug}**: final.mp4 is {mb:.1f} MB — too large for Webex attachment.\n"
                f"Fetch it from the server: `{final_mp4}`")

    return {
        "text": f"**{slug}** — final.mp4 ({mb:.1f} MB)",
        "files": [final_mp4],
    }


def cmd_storyfix(arg):
    """Regenerate a specific scene of a story with a targeted correction."""
    if not arg:
        return ("Usage: `storyfix <slug> <scene-number> <instruction>`\n"
                "Example: `storyfix story-the-invisible-backpack 3 show milo inside the kitchen window, not outside the house`")

    parts = arg.split(None, 2)
    if len(parts) < 3:
        return ("Usage: `storyfix <slug> <scene-number> <instruction>`\n"
                "Need all three: slug, scene number, and what to fix.")

    slug, scene_str, instruction = parts[0], parts[1], parts[2].strip()

    if not scene_str.isdigit():
        return f"Scene number must be an integer, got `{scene_str}`."
    scene_n = int(scene_str)

    project = project_get(slug)
    if not project:
        return f"No project found with slug `{slug}`."
    if (project.get("project_type") or "app") != "story":
        return f"`{slug}` is not a story project."

    project_dir = project["project_dir"]
    story_out = os.path.join(project_dir, "story-output")
    script_path = os.path.join(story_out, "script.md")
    scene_png = os.path.join(story_out, "images", f"scene-{scene_n}.png")

    if not os.path.exists(script_path):
        return f"`{slug}` has no script.md — can't fix without original prompts."
    if not os.path.exists(scene_png):
        return f"`{slug}` has no images/scene-{scene_n}.png — check scene number."

    # Write the fix-request file — spawner will read this on the next build
    fix_path = os.path.join(story_out, "fix-request.md")
    with open(fix_path, "w") as f:
        f.write(f"# Fix Request\n\n"
                f"**Scene:** {scene_n}\n\n"
                f"**Correction:**\n\n{instruction}\n")

    # Remove the bad image and the old final.mp4 so the rebuild picks fresh
    try:
        os.remove(scene_png)
    except OSError:
        pass
    final_mp4 = os.path.join(story_out, "final.mp4")
    try:
        os.remove(final_mp4)
    except OSError:
        pass

    # Re-queue the project so the orchestrator spawns a fix-mode Claude session
    import sqlite3
    db = get_db()
    db.execute(
        "UPDATE projects SET status='queued', deployed_url=NULL, completed_at=NULL, "
        "stall_alerted=0, last_state_change=datetime('now') WHERE slug=?",
        (slug,),
    )
    # Idempotent re-enqueue (don't duplicate if already in queue)
    cur = db.execute("SELECT id FROM queue WHERE project_id=?", (project["id"],))
    if not cur.fetchone():
        db.execute(
            "INSERT INTO queue (project_id, position) VALUES (?, "
            "COALESCE((SELECT MAX(position) FROM queue), 0) + 1)",
            (project["id"],),
        )
    db.commit()

    return (f"**Fix queued for `{slug}` scene {scene_n}**\n\n"
            f"**Instruction:** {instruction}\n\n"
            f"The orchestrator will regenerate just scene {scene_n} with nano-banana, "
            f"rebuild final.mp4, and notify when done. `fetchstory {slug}` to get the updated MP4.")


def cmd_stopall(_arg):
    """Stop all locally running deployed apps."""
    db = get_db()
    deployed = db.execute(
        "SELECT slug, port_start, port_end FROM projects WHERE status = 'deployed-local' AND port_start IS NOT NULL"
    ).fetchall()

    stopped = []
    for p in deployed:
        killed = False
        for port in range(p["port_start"], (p["port_end"] or p["port_start"]) + 1):
            try:
                result = subprocess.run(["fuser", f"{port}/tcp"], capture_output=True, text=True, timeout=5)
                if result.stdout.strip():
                    subprocess.run(["fuser", "-k", f"{port}/tcp"], capture_output=True, timeout=5)
                    killed = True
            except Exception:
                pass
        if killed:
            stopped.append(p["slug"])

    if stopped:
        return f"**Stopped {len(stopped)} apps:**\n" + "\n".join(f"- `{s}`" for s in stopped) + "\n\nUse `start <slug>` to restart individually, or `startall` to restart all."
    return "No running apps found."


def cmd_stop(slug):
    """Stop a single locally running app."""
    if not slug:
        return "Usage: `stop <slug>`"

    project = project_get(slug)
    if not project:
        return f"Project `{slug}` not found."

    if not project.get("port_start"):
        return f"Project `{slug}` has no port allocated."

    killed = False
    for port in range(project["port_start"], (project.get("port_end") or project["port_start"]) + 1):
        try:
            result = subprocess.run(["fuser", f"{port}/tcp"], capture_output=True, text=True, timeout=5)
            if result.stdout.strip():
                subprocess.run(["fuser", "-k", f"{port}/tcp"], capture_output=True, timeout=5)
                killed = True
        except Exception:
            pass

    if killed:
        return f"Stopped `{slug}` (ports {project['port_start']}-{project.get('port_end', project['port_start'])})"
    return f"Project `{slug}` wasn't running."


def cmd_start(slug):
    """Start a single locally deployed app."""
    if not slug:
        return "Usage: `start <slug>`"

    project = project_get(slug)
    if not project:
        return f"Project `{slug}` not found."

    if project["status"] not in ("deployed-local", "reviewing"):
        return f"Project `{slug}` is `{project['status']}` — can only start deployed apps."

    project_dir = project.get("project_dir", "")
    if not project_dir or not os.path.isdir(project_dir):
        return f"Project directory for `{slug}` not found."

    port = project.get("port_start")
    if not port:
        return f"Project `{slug}` has no port allocated."

    # Check if already running
    try:
        result = subprocess.run(["fuser", f"{port}/tcp"], capture_output=True, text=True, timeout=5)
        if result.stdout.strip():
            return f"Project `{slug}` is already running on port {port}."
    except Exception:
        pass

    # Use restart-apps logic to start it
    be_port = port + 1

    # Try backend
    started_be = False
    for be_dir_name in ["server", "backend"]:
        be_dir = os.path.join(project_dir, be_dir_name)
        for entry in ["index.js", "src/index.js"]:
            entry_path = os.path.join(be_dir, entry)
            if os.path.exists(entry_path):
                env = {**os.environ, "PORT": str(be_port), "HOST": "0.0.0.0"}
                subprocess.Popen(
                    ["node", entry],
                    cwd=be_dir, stdout=open(f"/tmp/{slug}-server.log", "w"),
                    stderr=subprocess.STDOUT, env=env,
                )
                started_be = True
                break
        if started_be:
            break

    # Try frontend
    started_fe = False
    for fe_dir_name in ["client", "frontend"]:
        fe_dir = os.path.join(project_dir, fe_dir_name)
        if os.path.isdir(fe_dir) and os.path.exists(os.path.join(fe_dir, "package.json")):
            subprocess.Popen(
                ["npx", "vite", "--host", "0.0.0.0", "--port", str(port)],
                cwd=fe_dir, stdout=open(f"/tmp/{slug}-client.log", "w"),
                stderr=subprocess.STDOUT,
            )
            started_fe = True
            break

    # Fallback: server-only on main port
    if not started_fe and not started_be:
        for entry in [
            os.path.join(project_dir, "server", "index.js"),
            os.path.join(project_dir, "server", "src", "index.js"),
            os.path.join(project_dir, "index.js"),
        ]:
            if os.path.exists(entry):
                env = {**os.environ, "PORT": str(port), "HOST": "0.0.0.0"}
                subprocess.Popen(
                    ["node", os.path.basename(entry)],
                    cwd=os.path.dirname(entry),
                    stdout=open(f"/tmp/{slug}.log", "w"),
                    stderr=subprocess.STDOUT, env=env,
                )
                started_be = True
                break

    parts = []
    if started_be:
        parts.append(f"backend on :{be_port}" if started_fe else f"server on :{port}")
    if started_fe:
        parts.append(f"frontend on :{port}")

    if parts:
        return f"Started `{slug}`: {', '.join(parts)}"
    return f"Could not determine how to start `{slug}`. Check project structure."


def cmd_gitpush(slug):
    """Push a project to a public GitHub repo."""
    if not slug:
        return "Usage: `gitpush <slug>`"

    project = project_get(slug)
    if not project:
        return f"Project `{slug}` not found."

    project_dir = project.get("project_dir", "")
    if not project_dir or not os.path.isdir(project_dir):
        return f"Project directory for `{slug}` not found."

    try:
        # Check if gh is available
        subprocess.run(["gh", "auth", "status"], capture_output=True, check=True, timeout=10)
    except Exception:
        return "GitHub CLI (`gh`) not authenticated. Run `gh auth login` on the server."

    try:
        # Create public repo and push
        result = subprocess.run(
            ["gh", "repo", "create", slug, "--public", "--source", ".", "--remote", "origin", "--push"],
            cwd=project_dir,
            capture_output=True, text=True, timeout=60,
        )

        if result.returncode == 0:
            # Extract repo URL from output
            repo_url = result.stdout.strip() or f"https://github.com/{slug}"
            return f"Project `{slug}` pushed to GitHub: {repo_url}"
        else:
            # Repo might already exist, try just pushing
            subprocess.run(["git", "add", "-A"], cwd=project_dir, capture_output=True, timeout=10)
            subprocess.run(
                ["git", "commit", "-m", "Update from Nightshift AutoFoundry"],
                cwd=project_dir, capture_output=True, timeout=10,
            )
            result2 = subprocess.run(
                ["git", "push", "-u", "origin", "HEAD"],
                cwd=project_dir, capture_output=True, text=True, timeout=30,
            )
            if result2.returncode == 0:
                return f"Project `{slug}` pushed to GitHub."
            return f"Git push failed: {result.stderr.strip()}\n{result2.stderr.strip()}"
    except Exception as e:
        return f"Failed to push to GitHub: {e}"


def cmd_pause(arg):
    if arg and arg.lower() == "all":
        return cmd_pauseall("")
    config_set("paused", "true")
    return "Queue paused. Active builds will continue but no new projects will be dequeued. Use `pause all` to also kill active builds."


def cmd_pauseall(_arg):
    """Pause queue AND kill all active Claude Code sessions."""
    config_set("paused", "true")

    # Kill all claude sessions
    try:
        result = subprocess.run(
            ["pkill", "-f", "claude.*dangerously-skip-permissions"],
            capture_output=True, timeout=10,
        )
    except Exception:
        pass

    # Count what was killed
    building = projects_by_status("building")
    killed_slugs = []
    for p in building:
        project_update(p["slug"], status="queued", stall_alerted=0)
        queue_enqueue(p["id"])
        killed_slugs.append(p["slug"])

    lines = ["**Everything stopped.**\n"]
    lines.append("Queue: **paused**")
    lines.append(f"Active sessions killed: **{len(killed_slugs)}**")
    if killed_slugs:
        lines.append(f"Re-queued: {', '.join(f'`{s}`' for s in killed_slugs)}")
    lines.append(f"\nUse `resume` when ready to restart.")

    return "\n".join(lines)


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


def _add_cloudflare_tunnel_route(hostname, service_url):
    """Add a tunnel ingress rule and DNS CNAME for a subdomain."""
    import requests as req

    cf_account = os.environ.get("CF_ACCOUNT_ID", "")
    cf_tunnel = os.environ.get("CF_TUNNEL_ID", "")
    cf_tunnel_token = os.environ.get("CF_TUNNEL_TOKEN", "")
    cf_dns_token = os.environ.get("CF_DNS_TOKEN", "")
    cf_zone = os.environ.get("CF_ZONE_ID", "")

    if not all([cf_account, cf_tunnel, cf_tunnel_token, cf_dns_token, cf_zone]):
        return "Cloudflare not configured"

    tunnel_headers = {"Authorization": f"Bearer {cf_tunnel_token}", "Content-Type": "application/json"}
    dns_headers = {"Authorization": f"Bearer {cf_dns_token}", "Content-Type": "application/json"}

    # Step 1: Get current tunnel config
    resp = req.get(
        f"https://api.cloudflare.com/client/v4/accounts/{cf_account}/cfd_tunnel/{cf_tunnel}/configurations",
        headers=tunnel_headers, timeout=15,
    )
    resp.raise_for_status()
    config = resp.json()["result"]["config"]
    ingress = config.get("ingress", [])

    # Check if route already exists
    if any(r.get("hostname") == hostname for r in ingress):
        return "route exists"

    # Insert new rule before the catch-all (last entry)
    new_rule = {"hostname": hostname, "service": service_url, "originRequest": {"noTLSVerify": True}}
    ingress.insert(-1, new_rule)  # Before the catch-all 404
    config["ingress"] = ingress

    # Step 2: Update tunnel config
    resp = req.put(
        f"https://api.cloudflare.com/client/v4/accounts/{cf_account}/cfd_tunnel/{cf_tunnel}/configurations",
        headers=tunnel_headers,
        json={"config": config},
        timeout=15,
    )
    resp.raise_for_status()

    # Step 3: Add CNAME DNS record
    cname_target = f"{cf_tunnel}.cfargotunnel.com"
    resp = req.post(
        f"https://api.cloudflare.com/client/v4/zones/{cf_zone}/dns_records",
        headers=dns_headers,
        json={
            "type": "CNAME",
            "name": hostname,
            "content": cname_target,
            "proxied": True,
        },
        timeout=15,
    )
    # 81057 = record already exists, that's fine
    if not resp.ok and resp.json().get("errors", [{}])[0].get("code") != 81057:
        resp.raise_for_status()

    return "ok"


def _remove_cloudflare_tunnel_route(hostname):
    """Remove a tunnel ingress rule and DNS CNAME for a subdomain."""
    import requests as req

    cf_account = os.environ.get("CF_ACCOUNT_ID", "")
    cf_tunnel = os.environ.get("CF_TUNNEL_ID", "")
    cf_tunnel_token = os.environ.get("CF_TUNNEL_TOKEN", "")
    cf_dns_token = os.environ.get("CF_DNS_TOKEN", "")
    cf_zone = os.environ.get("CF_ZONE_ID", "")

    if not all([cf_account, cf_tunnel, cf_tunnel_token, cf_dns_token, cf_zone]):
        return

    tunnel_headers = {"Authorization": f"Bearer {cf_tunnel_token}", "Content-Type": "application/json"}
    dns_headers = {"Authorization": f"Bearer {cf_dns_token}", "Content-Type": "application/json"}

    # Remove tunnel ingress rule
    try:
        resp = req.get(
            f"https://api.cloudflare.com/client/v4/accounts/{cf_account}/cfd_tunnel/{cf_tunnel}/configurations",
            headers=tunnel_headers, timeout=15,
        )
        resp.raise_for_status()
        config = resp.json()["result"]["config"]
        ingress = config.get("ingress", [])
        config["ingress"] = [r for r in ingress if r.get("hostname") != hostname]
        req.put(
            f"https://api.cloudflare.com/client/v4/accounts/{cf_account}/cfd_tunnel/{cf_tunnel}/configurations",
            headers=tunnel_headers, json={"config": config}, timeout=15,
        )
    except Exception:
        pass

    # Remove DNS CNAME
    try:
        resp = req.get(
            f"https://api.cloudflare.com/client/v4/zones/{cf_zone}/dns_records?type=CNAME&name={hostname}",
            headers=dns_headers, timeout=15,
        )
        for record in resp.json().get("result", []):
            req.delete(
                f"https://api.cloudflare.com/client/v4/zones/{cf_zone}/dns_records/{record['id']}",
                headers=dns_headers, timeout=15,
            )
    except Exception:
        pass


def cmd_promote(arg):
    """Promote: '<slug>' (app→Coolify) or 'study <slug> [--slug X]' (sws→seanmahoney.ai)."""
    kind, rest = _parse_kind_args(arg)
    if kind == "study":
        return _promote_study(rest)
    slug = arg.strip() if arg else ""
    if not slug:
        return "Usage: `promote <slug>` (app) or `promote study <slug>` (study guide)"
    project = project_get(slug)
    if not project:
        return f"Project `{slug}` not found."
    if project["status"] not in ("deployed-local", "reviewing"):
        return f"Project `{slug}` is `{project['status']}` — can only promote deployed or reviewing projects."

    project_dir = project.get("project_dir", "")
    if not project_dir or not os.path.isdir(project_dir):
        return f"Project directory for `{slug}` not found."

    coolify_url = os.environ.get("COOLIFY_API_URL", "")
    coolify_token = os.environ.get("COOLIFY_API_TOKEN", "")
    project_uuid = os.environ.get("COOLIFY_PROJECT_UUID", "")
    server_uuid = os.environ.get("COOLIFY_SERVER_UUID", "")
    env_name = os.environ.get("COOLIFY_ENVIRONMENT", "production")
    domain = os.environ.get("NSAF_DOMAIN", "seanmahoney.ai")

    if not all([coolify_url, coolify_token, project_uuid, server_uuid]):
        return "Coolify not configured."

    import requests as req

    lines = [f"**Promoting `{slug}` to {slug}.{domain}**\n"]

    # Detect git branch
    try:
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=project_dir, capture_output=True, text=True, timeout=5,
        )
        git_branch = branch_result.stdout.strip() or "main"
    except Exception:
        git_branch = "main"

    # Step 0: Generate Dockerfile if needed
    dockerfile_path = os.path.join(project_dir, "Dockerfile")
    if not os.path.exists(dockerfile_path):
        try:
            # Run the dockerize script via node
            nsaf_dir = os.environ.get("NSAF_DIR", os.path.join(os.path.dirname(__file__), "..", ".."))
            result = subprocess.run(
                ["node", "-e", f"""
import {{ generateDockerfile }} from './orchestrator/src/dockerize.js';
const result = generateDockerfile('{project_dir}');
console.log(result ? 'ok' : 'failed');
"""],
                cwd=nsaf_dir, capture_output=True, text=True, timeout=15,
            )
            if "ok" in result.stdout:
                # Commit the Dockerfile
                subprocess.run(["git", "add", "Dockerfile"], cwd=project_dir, capture_output=True, timeout=5)
                subprocess.run(["git", "add", "-A"], cwd=project_dir, capture_output=True, timeout=5)
                subprocess.run(
                    ["git", "commit", "-m", "Add Dockerfile for Coolify deployment"],
                    cwd=project_dir, capture_output=True, timeout=10,
                )
                lines.append("0. Dockerfile generated")
            else:
                lines.append("0. Dockerfile generation failed — may need manual Dockerfile")
        except Exception as e:
            lines.append(f"0. Dockerfile generation error: {e}")
    else:
        lines.append("0. Dockerfile exists")

    # Step 0.5: Generate README.md
    try:
        readme_path = os.path.join(project_dir, "README.md")
        idea = None
        if project.get("idea_id"):
            idea = idea_get(project["idea_id"])

        # Gather project info
        app_name = idea["name"] if idea else slug
        app_desc = idea["description"] if idea else "A web application built by Nightshift AutoFoundry."
        app_category = idea.get("category", "") if idea else ""
        app_complexity = idea.get("complexity", "") if idea else ""
        app_stack = ""
        if idea and idea.get("suggested_stack"):
            import json as _json
            try:
                stack = _json.loads(idea["suggested_stack"]) if isinstance(idea["suggested_stack"], str) else idea["suggested_stack"]
                app_stack = ", ".join(f"{v}" for v in stack.values())
            except Exception:
                pass

        subdomain_url = f"https://{slug}.{domain}"

        # Scan for notable files
        has_client = os.path.isdir(os.path.join(project_dir, "client")) or os.path.isdir(os.path.join(project_dir, "frontend"))
        has_server = os.path.isdir(os.path.join(project_dir, "server")) or os.path.isdir(os.path.join(project_dir, "backend"))

        # Read test report if available
        test_summary = ""
        for test_file in ["sdd-output/tests/test-report.md", "sdd-output/tests/pipeline-report.md"]:
            tp = os.path.join(project_dir, test_file)
            if os.path.exists(tp):
                with open(tp) as f:
                    content = f.read()
                # Extract pass/fail counts
                import re
                match = re.search(r"(\d+).*pass", content, re.IGNORECASE)
                if match:
                    test_summary = f"{match.group(0)}"
                break

        # Build README
        readme_lines = [
            f"# {app_name}\n",
            f"{app_desc}\n",
            f"**Live:** [{subdomain_url}]({subdomain_url})\n",
        ]

        if app_category or app_complexity:
            readme_lines.append(f"**Category:** {app_category} | **Complexity:** {app_complexity}\n")

        if app_stack:
            readme_lines.append(f"**Tech Stack:** {app_stack}\n")

        readme_lines.append("## Getting Started\n")
        readme_lines.append("```bash")
        readme_lines.append("# Clone and install")
        readme_lines.append(f"git clone https://github.com/seanerama/{slug}.git")
        readme_lines.append(f"cd {slug}")
        if has_server and has_client:
            client_dir = "client" if os.path.isdir(os.path.join(project_dir, "client")) else "frontend"
            server_dir = "server" if os.path.isdir(os.path.join(project_dir, "server")) else "backend"
            readme_lines.append(f"cd {server_dir} && npm install && cd ../")
            readme_lines.append(f"cd {client_dir} && npm install && cd ../")
            readme_lines.append("")
            readme_lines.append("# Set up environment")
            readme_lines.append("cp .env.example .env  # Edit with your database URL")
            readme_lines.append("")
            readme_lines.append("# Run development")
            readme_lines.append(f"npm --prefix {server_dir} run dev  # Backend")
            readme_lines.append(f"npm --prefix {client_dir} run dev  # Frontend")
        else:
            readme_lines.append("npm install")
            readme_lines.append("cp .env.example .env  # Edit with your config")
            readme_lines.append("npm start")
        readme_lines.append("```\n")

        readme_lines.append("## Docker\n")
        readme_lines.append("```bash")
        readme_lines.append("docker build -t " + slug + " .")
        readme_lines.append("docker run -p 3000:3000 --env-file .env " + slug)
        readme_lines.append("```\n")

        if test_summary:
            readme_lines.append(f"## Tests\n")
            readme_lines.append(f"{test_summary}\n")

        readme_lines.append("---\n")
        readme_lines.append("*Built by [Nightshift AutoFoundry](https://github.com/seanerama/nsaf)*")

        with open(readme_path, "w") as f:
            f.write("\n".join(readme_lines) + "\n")

        subprocess.run(["git", "add", "README.md"], cwd=project_dir, capture_output=True, timeout=5)
        subprocess.run(
            ["git", "commit", "-m", "Add README for GitHub"],
            cwd=project_dir, capture_output=True, timeout=10,
        )
        lines.append("0.5. README.md generated")
    except Exception as e:
        lines.append(f"0.5. README generation failed: {e}")

    # Step 1: Push to GitHub
    try:
        result = subprocess.run(
            ["gh", "repo", "view", f"seanerama/{slug}", "--json", "name"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            subprocess.run(
                ["gh", "repo", "create", slug, "--public", "--source", ".", "--remote", "origin", "--push"],
                cwd=project_dir, capture_output=True, text=True, timeout=60,
            )
            lines.append(f"1. GitHub: `seanerama/{slug}` created")
        else:
            subprocess.run(["git", "add", "-A"], cwd=project_dir, capture_output=True, timeout=10)
            subprocess.run(
                ["git", "commit", "-m", "Update from Nightshift AutoFoundry", "--allow-empty"],
                cwd=project_dir, capture_output=True, timeout=10,
            )
            subprocess.run(
                ["git", "push", "-u", "origin", "HEAD"],
                cwd=project_dir, capture_output=True, text=True, timeout=30,
            )
            lines.append(f"1. GitHub: `seanerama/{slug}` updated")
    except Exception as e:
        lines.append(f"1. GitHub failed: {e}")
        return "\n".join(lines)

    # Step 2: Create app in Coolify
    repo_url = f"https://github.com/seanerama/{slug}"
    subdomain_url = f"https://{slug}.{domain}"

    try:
        resp = req.post(
            f"{coolify_url}/api/v1/applications/public",
            headers={"Authorization": f"Bearer {coolify_token}", "Content-Type": "application/json"},
            json={
                "project_uuid": project_uuid,
                "environment_name": env_name,
                "server_uuid": server_uuid,
                "type": "public",
                "name": slug,
                "git_repository": repo_url,
                "git_branch": git_branch,
                "build_pack": "dockerfile",
                "dockerfile_location": "/Dockerfile",
                "ports_exposes": "3000",
                "domains": subdomain_url,
            },
            timeout=30,
        )
        resp.raise_for_status()
        app_data = resp.json()
        app_uuid = app_data.get("uuid", "")
        lines.append(f"2. Coolify: app `{app_uuid}` created")
    except Exception as e:
        lines.append(f"2. Coolify failed: {e}")
        return "\n".join(lines)

    # Step 3: Set environment variables in Coolify
    coolify_headers = {"Authorization": f"Bearer {coolify_token}", "Content-Type": "application/json"}
    env_url = f"{coolify_url}/api/v1/applications/{app_uuid}/envs"

    # Database URL — use host.docker.internal to reach host PostgreSQL from container
    pg_user = os.environ.get("POSTGRES_USER", "nsaf_admin")
    pg_pass = os.environ.get("POSTGRES_PASSWORD", "")
    pg_host = "host.docker.internal"
    pg_port = os.environ.get("POSTGRES_PORT", "5432")
    db_name = project.get("db_name") or f"nsaf_{slug.replace('-', '_')}"

    env_vars = {
        "DATABASE_URL": f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{db_name}",
        "PORT": "3000",
        "NODE_ENV": "production",
        "CORS_ORIGIN": subdomain_url,
    }

    env_set_count = 0
    for key, value in env_vars.items():
        try:
            req.post(env_url, headers=coolify_headers,
                     json={"key": key, "value": value, "is_preview": False}, timeout=10)
            env_set_count += 1
        except Exception:
            pass
    lines.append(f"3. Coolify: {env_set_count} env vars set")

    # Step 4: Trigger deploy
    try:
        resp = req.post(
            f"{coolify_url}/api/v1/deploy",
            headers=coolify_headers,
            json={"uuid": app_uuid},
            timeout=30,
        )
        resp.raise_for_status()
        lines.append(f"4. Coolify: build triggered")
    except Exception as e:
        lines.append(f"4. Coolify deploy failed: {e}")

    # Step 5: Cloudflare tunnel route + DNS
    hostname = f"{slug}.{domain}"
    # Coolify assigns a port — for now route to Coolify's Traefik proxy
    service_url = "https://localhost:443"  # Coolify's Traefik proxy (HTTPS, TLS verified by Cloudflare)

    try:
        result = _add_cloudflare_tunnel_route(hostname, service_url)
        if result == "ok":
            lines.append(f"5. Cloudflare: tunnel route + DNS CNAME added")
        elif result == "route exists":
            lines.append(f"5. Cloudflare: route already exists")
        else:
            lines.append(f"5. Cloudflare: {result}")
    except Exception as e:
        lines.append(f"5. Cloudflare failed: {e}")

    # Step 6: Update project status
    project_update(slug, status="promoted", render_url=subdomain_url)
    lines.append(f"6. Status: promoted")
    lines.append(f"\n**Live at:** {subdomain_url}")
    lines.append(f"**Coolify:** {coolify_url}")

    return "\n".join(lines)


# Light-mode → dark-mode CSS variable swap for study guide HTML.
# Keys are the light-mode declaration, values are the dark-mode replacement.
_STUDY_GUIDE_DARK_MODE_SWAPS = [
    ("--color-bg: #fafafa",                    "--color-bg: #0a0a0f"),
    ("--color-surface: #ffffff",               "--color-surface: #1a1d2e"),
    ("--color-text: #1a1a1a",                  "--color-text: #e0e0e8"),
    ("--color-muted: #6b7280",                 "--color-muted: #9ca3af"),
    ("--color-primary: #2563eb",               "--color-primary: #818cf8"),
    ("--color-primary-light: #dbeafe",         "--color-primary-light: #1e1b4b"),
    ("--color-success: #16a34a",               "--color-success: #4ade80"),
    ("--color-success-light: #dcfce7",         "--color-success-light: #052e16"),
    ("--color-error: #dc2626",                 "--color-error: #f87171"),
    ("--color-error-light: #fee2e2",           "--color-error-light: #450a0a"),
    ("--color-border: #e5e7eb",                "--color-border: #2a2f42"),
    ("--color-quiz-bg: #f0f4ff",               "--color-quiz-bg: #12151f"),
    ("--color-keypoints-bg: #fffbeb",          "--color-keypoints-bg: #1a1700"),
    ("--color-keypoints-border: #f59e0b",      "--color-keypoints-border: #d97706"),
    ("--shadow: 0 1px 3px rgba(0,0,0,0.1)",    "--shadow: 0 1px 3px rgba(0,0,0,0.4)"),
]


def _find_sws_output_dir(project_dir):
    """SWS layout: <project_dir>/output/<topic-slug>/{guides,chapters,textbook.md}."""
    output_root = os.path.join(project_dir, "output")
    if not os.path.isdir(output_root):
        return None
    for entry in sorted(os.listdir(output_root)):
        candidate = os.path.join(output_root, entry)
        if os.path.isdir(os.path.join(candidate, "guides")) and os.path.isdir(os.path.join(candidate, "chapters")):
            return candidate
    return None


def _extract_chapter_title(md_path):
    """Pull the first '## Chapter N: Title' (or '# Title') heading from a chapter md."""
    import re
    try:
        with open(md_path) as f:
            for _ in range(20):
                line = f.readline()
                if not line:
                    break
                m = re.match(r"^#{1,3}\s*(?:Chapter\s*\d+\s*[:\-]\s*)?(.+?)\s*$", line)
                if m and m.group(1).strip():
                    return m.group(1).strip()
    except OSError:
        pass
    return None


def _next_study_guide_order(repo_dir):
    import re
    yaml_dir = os.path.join(repo_dir, "src", "content", "studyGuides")
    highest = 0
    if os.path.isdir(yaml_dir):
        for fn in os.listdir(yaml_dir):
            if not fn.endswith(".yaml"):
                continue
            try:
                with open(os.path.join(yaml_dir, fn)) as f:
                    for line in f:
                        m = re.match(r"^order:\s*(\d+)", line)
                        if m:
                            highest = max(highest, int(m.group(1)))
                            break
            except OSError:
                continue
    return highest + 1


def _yaml_quote(s):
    """Minimal YAML double-quoted string escape for title/description fields."""
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _run_git(repo, *args, check=True, capture=True):
    """Run a git command in the website repo. Returns CompletedProcess."""
    return subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=capture, text=True, check=check, timeout=120,
    )


def _promote_study(rest):
    """Deploy an SWS project's output to seanmahoney.ai via the Astro repo."""
    import re
    import shutil

    if not rest:
        return ("Usage: `promote study <sws-slug> [--slug web-slug]`\n"
                "Example: `promote study sws-ccie-automation --slug ccie-automation`")

    web_slug_override, rest = _extract_flag(rest, "slug")
    project_slug = rest.strip().split()[0] if rest.strip() else ""
    if not project_slug:
        return "Usage: `promote study <sws-slug> [--slug web-slug]`"

    project = project_get(project_slug)
    if not project:
        return f"Project `{project_slug}` not found."
    if (project.get("project_type") or "app") != "studyws":
        return f"`{project_slug}` is project_type `{project.get('project_type')}`, not `studyws`."

    project_dir = project.get("project_dir", "")
    if not project_dir or not os.path.isdir(project_dir):
        return f"Project directory for `{project_slug}` not found."

    repo = os.environ.get("NSAF_WEBSITE_REPO", "")
    bun = os.environ.get("BUN_PATH", "bun")
    if not repo or not os.path.isdir(repo):
        return ("`NSAF_WEBSITE_REPO` is not set or directory does not exist. "
                "Set it in `.env` to the cloned website repo path.")

    sws_out = _find_sws_output_dir(project_dir)
    if not sws_out:
        return f"No SWS output dir found under `{project_dir}/output/*/{{guides,chapters}}`."

    guides_src = os.path.join(sws_out, "guides")
    chapters_src = os.path.join(sws_out, "chapters")
    textbook_src = os.path.join(sws_out, "textbook.md")

    html_files = sorted(f for f in os.listdir(guides_src) if re.match(r"chapter-\d+\.html$", f))
    if not html_files:
        return f"No `chapter-NN.html` files found in `{guides_src}`."

    # Map chapter-NN.html -> chapter-NN.md to extract the chapter title
    chapter_titles = []
    for html_name in html_files:
        md_name = html_name.replace(".html", ".md")
        md_path = os.path.join(chapters_src, md_name)
        title = _extract_chapter_title(md_path) if os.path.isfile(md_path) else None
        chapter_titles.append((html_name, title or html_name.replace(".html", "")))

    web_slug = (web_slug_override or "").strip() or re.sub(r"^sws-", "", project_slug)
    web_slug = re.sub(r"[^a-z0-9-]+", "-", web_slug.lower()).strip("-")
    if not web_slug:
        return f"Could not derive a web slug from `{project_slug}`. Pass `--slug` explicitly."

    yaml_path = os.path.join(repo, "src", "content", "studyGuides", f"{web_slug}.yaml")
    target_dir = os.path.join(repo, "public", "study-guides", web_slug)
    textbook_dst = os.path.join(repo, "src", "content", "textbooks", f"{web_slug}.md")

    if os.path.exists(yaml_path) or os.path.isdir(target_dir):
        return (f"Study guide `{web_slug}` already exists in the website repo. "
                f"Delete it first or pass `--slug <other-name>`.")

    lines = [f"**Promoting study guide `{project_slug}` → `{web_slug}`**\n"]

    # Step 1: ensure repo is clean and up to date
    try:
        _run_git(repo, "fetch", "origin", "main")
        status = _run_git(repo, "status", "--porcelain").stdout.strip()
        if status:
            return (f"Website repo at `{repo}` has uncommitted changes:\n```\n{status}\n```\n"
                    f"Commit or stash them on the laptop, push, then retry.")
        _run_git(repo, "pull", "--ff-only", "origin", "main")
    except subprocess.CalledProcessError as e:
        return f"Failed to sync website repo: {e.stderr or e.stdout}"

    # Step 2: copy HTML guides + dark-mode CSS swap
    os.makedirs(target_dir, exist_ok=True)
    swapped_count = 0
    for html_name in html_files:
        src = os.path.join(guides_src, html_name)
        dst = os.path.join(target_dir, html_name)
        with open(src) as f:
            content = f.read()
        if "--color-bg: #fafafa" in content:
            for old, new in _STUDY_GUIDE_DARK_MODE_SWAPS:
                content = content.replace(old, new)
            swapped_count += 1
        with open(dst, "w") as f:
            f.write(content)
    lines.append(
        f"1. Copied {len(html_files)} HTML guide(s)"
        + (f" (dark-mode swapped: {swapped_count})" if swapped_count else " (already dark-mode)")
    )

    # Step 3: write YAML
    order = _next_study_guide_order(repo)
    title = (project.get("slug") or web_slug).replace("sws-", "").replace("-", " ").title()
    desc = f"Study guide for {title} — generated by NSAF StudyWS pipeline."
    with open(yaml_path, "w") as f:
        f.write(f"title: {_yaml_quote(title)}\n")
        f.write(f'slug: "{web_slug}"\n')
        f.write(f"description: {_yaml_quote(desc)}\n")
        f.write(f"order: {order}\n")
        f.write("chapters:\n")
        for html_name, ch_title in chapter_titles:
            f.write(f"  - title: {_yaml_quote(ch_title)}\n")
            f.write(f'    htmlFile: "{html_name}"\n')
    lines.append(f"2. Wrote YAML at order={order}: `{web_slug}.yaml`")

    # Step 4: textbook companion (optional)
    has_textbook = os.path.isfile(textbook_src)
    if has_textbook:
        with open(textbook_src) as f:
            text = f.read()
        h1_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        book_title = h1_match.group(1).strip() if h1_match else title
        os.makedirs(os.path.dirname(textbook_dst), exist_ok=True)
        with open(textbook_dst, "w") as f:
            f.write(f"---\n")
            f.write(f"title: {_yaml_quote(book_title)}\n")
            f.write(f'studyGuideSlug: "{web_slug}"\n')
            f.write(f"---\n\n")
            f.write(text)
        lines.append(f"3. Wrote textbook companion: `textbooks/{web_slug}.md`")
    else:
        lines.append("3. No textbook.md present — skipping companion")

    # Step 5: bun verify build
    try:
        result = subprocess.run(
            [bun, "run", "build"], cwd=repo,
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode != 0:
            tail = (result.stderr or result.stdout).splitlines()[-15:]
            # Roll back our changes — repo was clean before we started
            _run_git(repo, "reset", "--hard", "HEAD", capture=False, check=False)
            _run_git(repo, "clean", "-fd", capture=False, check=False)
            lines.append(f"4. ❌ `bun run build` failed — changes reverted.\n```\n" + "\n".join(tail) + "\n```")
            return "\n".join(lines)
    except subprocess.TimeoutExpired:
        _run_git(repo, "reset", "--hard", "HEAD", capture=False, check=False)
        _run_git(repo, "clean", "-fd", capture=False, check=False)
        lines.append("4. ❌ `bun run build` timed out after 5 minutes — changes reverted.")
        return "\n".join(lines)
    lines.append(f"4. ✅ `bun run build` passed")

    # Step 6: commit + push
    try:
        _run_git(repo, "add",
                 f"public/study-guides/{web_slug}",
                 f"src/content/studyGuides/{web_slug}.yaml")
        if has_textbook:
            _run_git(repo, "add", f"src/content/textbooks/{web_slug}.md")
        commit_msg = f"Add {title} study guide ({len(html_files)} chapters)"
        _run_git(repo, "commit", "-m", commit_msg)
        _run_git(repo, "push", "origin", "main")
    except subprocess.CalledProcessError as e:
        lines.append(f"5. ❌ git commit/push failed: {(e.stderr or e.stdout).strip()}")
        return "\n".join(lines)
    lines.append(f"5. Pushed to `origin/main` — Cloudflare Pages will auto-deploy")

    domain = os.environ.get("NSAF_DOMAIN", "seanmahoney.ai")
    lines.append(f"\n**Live in ~60s at:** https://{domain}/study-guides/{web_slug}/chapter-01.html")
    if has_textbook:
        lines.append(f"**Textbook:** https://{domain}/study-guides/{web_slug}/textbook")

    return "\n".join(lines)


def cmd_help(_arg):
    return """**Nightshift AutoFoundry Commands**

**Build Management**
- `status` — Queue depth, active builds, completions
- `pause` — Stop dequeuing (active builds continue)
- `pause all` — Stop everything: pause queue + kill active builds
- `resume` — Resume the build queue
- `skip <slug>` — Scrap a project
- `restart <slug>` — Re-queue a stalled project
- `rebuild <slug> [notes]` — Full rebuild with optional notes
- `modify <slug> <changes>` — Apply changes to existing build

**Ideas**
- `ideas` / `ideas 2` / `ideas openai` — List today's app ideas (paginate / filter by source)
- `stories` / `studies` — List today's story / study ideas (same paging + filters)
- `idea <id>` — Detail for an app idea
- `idea story <id>` / `idea study <id>` — Detail for a story / study idea
- `idea <free-form text>` — Brainstorm: Claude expands the idea + drafts a vision doc
- `queue <id>` — Add an app idea to the build queue
- `queue story <id>` / `queue study <id>` — Build a story / study from a generated idea
- `generate` — Trigger new app idea generation
- `generate stories [N]` — Generate children's story ideas (per-provider count, default 10)
- `generate studies [N]` — Generate study plan / textbook topic ideas

**Vision Sessions** (refine an idea before building)
- `vision list` — List recent vision sessions
- `vision show <slug>` — Show the full vision doc
- `vision questions <slug>` — Show just the open questions (mobile-friendly)
- `vision answer <slug> <N> <text>` — Answer one question in Webex
- `vision answers <slug> <text>` — Replace all answers in one shot
- `vision review <slug>` — Claude reviews answers, suggests follow-ups
- `vision email <slug>` — Email the .md (better for laptop editing)
- `vision <slug>` (attach edited .md) — Replace the doc with your edited version
- `vision build <slug> [story|studyws|app]` — Promote to a real project + queue
- `vision cancel <slug>` — Drop a session

**Lifecycle**
- `promote <slug>` — Push to GitHub + deploy via Coolify to *.seanmahoney.ai
- `promote study <slug> [--slug name]` — Deploy an SWS project to seanmahoney.ai/study-guides/&lt;name&gt;
- `demote <slug>` — Remove from Coolify, revert to local
- `archive <slug>` — Stop locally, release ports, keep files
- `delete <id> [id...]` — Permanently delete projects
- `gitpush <slug>` — Push to a public GitHub repo
- `export` / `export ideas` — Download CSV of app ideas + projects
- `export stories` / `export studies` — Download CSV of generated story / study ideas
- `export all` — Download a ZIP containing all three CSVs

**Content Generation**
- `sws <topic>` — Generate a textbook + study guides for a topic
- `sws <url>` — Generate from a PDF/document (e.g. exam blueprint)
- `sws <topic> --chapters 12 --level beginner` — With options
- `story <idea>` — Generate an illustrated audio story (MP4)
- `story <idea> --title kind-boy` — Set a short slug for the project
- `story <idea> --scenes 8 --style "watercolor" --notes "..."` — With options
- `fetchstory <slug>` — Fetch the final MP4 for a completed story
- `storyfix <slug> <scene-n> <what to fix>` — Regenerate one scene with a targeted correction and rebuild

**App Control**
- `stop <slug>` — Stop a running local app
- `start <slug>` — Start a stopped local app
- `stopall` — Stop all running local apps

**Troubleshooting**
- `debug <slug> <problem>` — Diagnose and fix a deployed app

**Monitoring**
- `system` — CPU, memory, disk, active sessions
- `tokens [hours]` — Build activity (default 24h)
- `help` — Show this message"""
