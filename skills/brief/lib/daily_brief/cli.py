"""The ``brief`` CLI — the deterministic boundary the slash commands call.

Does NO AI work. See contracts/cli-interface.md. Stage 1 provides ``init`` and ``status``;
later stages add history/dedup, render, setup, and kb commands.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from . import __version__
from .dedup import annotate
from .history import append_history, read_history
from .knowledge_base import append_kb
from .models import BriefItem, BriefRun, Failure, HistoryEntry
from .paths import brief_dir, data_root
from .profiles import list_profiles, load_profile
from .render import build_podcast_prompt, render_html, render_summary
from .setup import ensure_general, scaffold_profile
from .status import gather_status

app = typer.Typer(help="Daily-Brief: personal, profile-aware news catch-up.", no_args_is_help=True)


def _load_json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


@app.command()
def init(
    force: bool = typer.Option(False, "--force", help="Overwrite the General profile."),
) -> None:
    """Create the data/ tree and the built-in General profile."""
    root = data_root()
    (root / "profiles").mkdir(parents=True, exist_ok=True)
    (root / "briefs").mkdir(parents=True, exist_ok=True)
    ref = ensure_general(force=force)
    typer.echo(f"Initialized data dir at {root}")
    typer.echo(f"General profile: {ref}")


@app.command()
def status(json_out: bool = typer.Option(False, "--json", help="Emit JSON.")) -> None:
    """Show profiles, history counts, and last runs."""
    report = gather_status()
    if json_out:
        typer.echo(json.dumps({"version": __version__, **report}))
        return
    typer.echo(f"Daily-Brief v{__version__}")
    if not report["profiles"]:
        typer.echo("No profiles yet. Run `brief init`.")
        return
    for p in report["profiles"]:
        last = p["last_run"]
        if last:
            s = last["stats"]
            last_str = (
                f"last run {last['timestamp']} "
                f"({s.get('items_total', 0)} items, {s.get('items_new', 0)} new)"
            )
        else:
            last_str = "no runs yet"
        typer.echo(
            f"  - {p['slug']}  ({p['title']}) — {p['topics']} topic(s), "
            f"{p['history_entries']} history, {last_str}"
        )
    t = report["totals"]
    typer.echo(
        f"Totals: {t['profiles']} profile(s), {t['runs']} run(s), "
        f"{t['history_entries']} history entries."
    )


profile_app = typer.Typer(help="Profile commands.", no_args_is_help=True)
app.add_typer(profile_app, name="profile")


@profile_app.command("list")
def profile_list(json_out: bool = typer.Option(False, "--json", help="Emit JSON.")) -> None:
    """List profile slugs and titles."""
    profiles = list_profiles()
    if json_out:
        typer.echo(json.dumps([{"slug": s, "title": t} for s, t in profiles]))
        return
    for slug, title in profiles:
        typer.echo(f"{slug}\t{title}")


@profile_app.command("show")
def profile_show(
    slug: str, json_out: bool = typer.Option(False, "--json", help="Emit JSON.")
) -> None:
    """Dump a parsed profile."""
    prof = load_profile(slug)
    if json_out:
        typer.echo(prof.model_dump_json())
        return
    typer.echo(f"{prof.slug} — {prof.title}")
    typer.echo(prof.description)
    for t in prof.topics:
        typer.echo(f"  • {t.name} (web_search={t.web_search}, {len(t.sources)} source(s))")


@profile_app.command("create")
def profile_create(
    slug: str,
    title: str = typer.Option(..., "--title"),
    description: str = typer.Option(..., "--description"),
    from_sample: bool = typer.Option(False, "--from-sample", help="Seed with sample topics."),
    force: bool = typer.Option(False, "--force", help="Overwrite an existing reference.md."),
) -> None:
    """Scaffold a new profile reference.md (+ empty history/KB)."""
    path = scaffold_profile(slug, title, description, from_sample=from_sample, force=force)
    typer.echo(str(path))


history_app = typer.Typer(help="History log commands.", no_args_is_help=True)
app.add_typer(history_app, name="history")


@history_app.command("add")
def history_add(
    slug: str,
    json_file: str = typer.Option(..., "--json-file", help="JSON list of HistoryEntry objects."),
) -> None:
    """Append history entries from a JSON file. Prints the number appended."""
    rows = [HistoryEntry.model_validate(r) for r in _load_json(json_file)]
    count = append_history(slug, rows)
    typer.echo(str(count))


@app.command()
def dedup(
    slug: str,
    items_file: str = typer.Option(..., "--items-file", help="JSON list of BriefItem objects."),
    mode: str = typer.Option("annotate", "--mode", help="annotate | drop"),
) -> None:
    """Annotate (or drop) items against the profile's history; prints resulting items as JSON."""
    items = [BriefItem.model_validate(r) for r in _load_json(items_file)]
    result = annotate(items, read_history(slug), mode=mode)
    typer.echo(json.dumps([i.model_dump() for i in result]))


@app.command("kb-append")
def kb_append(
    slug: str,
    json_file: str = typer.Option(..., "--json-file", help='{"date": "...", "learnings": [...]}'),
) -> None:
    """Append dated learnings to the profile's knowledge base. Prints the number written."""
    payload = _load_json(json_file)
    count = append_kb(slug, payload.get("learnings", []), payload.get("date", ""))
    typer.echo(str(count))


@app.command("run-dir")
def run_dir(
    slug: str,
    timestamp: str = typer.Option(..., "--timestamp", help="YYYY-MM-DD-HHMM."),
) -> None:
    """Create and print a run directory path."""
    out = brief_dir(slug, timestamp)
    out.mkdir(parents=True, exist_ok=True)
    typer.echo(str(out))


@app.command()
def assemble(
    slug: str,
    timestamp: str,
    trigger: str = typer.Option(..., "--trigger", help="run | topic"),
    started_at: str = typer.Option(..., "--started-at", help="ISO datetime of the run."),
    items_file: str = typer.Option(..., "--items-file", help="JSON list of deduped+framed items."),
    requested_topic: str | None = typer.Option(None, "--requested-topic"),
    failures_file: str | None = typer.Option(None, "--failures-file", help="JSON failures list."),
) -> None:
    """Assemble a BriefRun (with computed stats), write run.json, and print its path."""
    items = [BriefItem.model_validate(r) for r in _load_json(items_file)]
    failures = (
        [Failure.model_validate(r) for r in _load_json(failures_file)] if failures_file else []
    )
    prior = sum(1 for i in items if i.prior_coverage)
    stats = {
        "items_total": len(items),
        "items_new": len(items) - prior,
        "items_prior": prior,
        "sources_failed": len(failures),
    }
    run = BriefRun(
        profile=slug,
        trigger=trigger,
        requested_topic=requested_topic,
        started_at=started_at,
        items=items,
        failures=failures,
        stats=stats,
    )
    out = brief_dir(slug, timestamp)
    out.mkdir(parents=True, exist_ok=True)
    run_json = out / "run.json"
    run_json.write_text(run.model_dump_json(indent=2), encoding="utf-8")
    typer.echo(str(run_json))


@app.command("history-from-run")
def history_from_run(slug: str, timestamp: str) -> None:
    """Derive history entries from a run's run.json and append them. Prints the count."""
    run = BriefRun.model_validate(_load_json(str(brief_dir(slug, timestamp) / "run.json")))
    date = run.started_at[:10]
    entries = [
        HistoryEntry(date=date, topic=i.topic, title=i.title, source=i.source.name,
                     url=i.url, dedup_key=i.id)
        for i in run.items
    ]
    typer.echo(str(append_history(slug, entries)))


@app.command()
def render(
    slug: str,
    timestamp: str,
    run_file: str | None = typer.Option(
        None, "--run-file", help="BriefRun JSON (default: <run-dir>/run.json)."
    ),
) -> None:
    """Render brief.html + summary.md into the run dir from a BriefRun JSON file."""
    out = brief_dir(slug, timestamp)
    rf = run_file or str(out / "run.json")
    run = BriefRun.model_validate(_load_json(rf))
    out.mkdir(parents=True, exist_ok=True)
    html_path = out / "brief.html"
    summary_path = out / "summary.md"
    html_path.write_text(render_html(run), encoding="utf-8")
    summary_path.write_text(render_summary(run), encoding="utf-8")
    typer.echo(str(html_path))
    typer.echo(str(summary_path))


@app.command("podcast-prompt")
def podcast_prompt(slug: str, timestamp: str) -> None:
    """Build the podcast deep-dive prompt from the run's summary.md (prints to stdout)."""
    summary_path = brief_dir(slug, timestamp) / "summary.md"
    summary_md = summary_path.read_text(encoding="utf-8") if summary_path.exists() else ""
    typer.echo(build_podcast_prompt(summary_md, load_profile(slug)))


if __name__ == "__main__":
    app()
