"""Stage 5: offline replay of the orchestration pipeline via the CLI.

Simulates what the /brief:run command's deterministic steps do, using fixture research data
instead of live sub-agents/MCP: dedup -> assemble -> render -> history -> podcast-prompt.
"""

from __future__ import annotations

import json

from typer.testing import CliRunner

from daily_brief.cli import app
from daily_brief.paths import brief_dir, history_path

runner = CliRunner()


def _run(*args):
    result = runner.invoke(app, list(args))
    assert result.exit_code == 0, result.output
    return result.output


def _write(path, obj):
    path.write_text(json.dumps(obj), encoding="utf-8")


def test_full_offline_pipeline(data_dir):
    _run("init")
    _run("profile", "create", "ai", "--title", "AI", "--description",
         "an ai engineer who ships LLM products", "--from-sample")

    # Seed history so dedup has something to annotate.
    hist = [{
        "date": "2026-06-01", "topic": "Model releases", "title": "Opus preview",
        "source": "TechCrunch", "url": "https://example.com/opus",
        "dedup_key": "url:https://example.com/opus",
    }]
    hist_file = data_dir / "hist.json"
    _write(hist_file, hist)
    _run("history", "add", "ai", "--json-file", str(hist_file))

    # Raw items = flattened ResearchResult items (orchestrator step 3).
    raw = [
        {"id": "", "title": "Anthropic ships Opus 4.8", "summary": "1M context",
         "source": {"name": "Perplexity", "type": "web-search"},
         "url": "https://example.com/opus?utm_source=x", "topic": "Model releases"},
        {"id": "", "title": "Agent platform wars", "summary": "orchestration moat",
         "source": {"name": "Stratechery", "type": "blog"},
         "url": "https://stratechery.com/agents", "topic": "AI agents"},
    ]
    raw_file = data_dir / "raw.json"
    _write(raw_file, raw)

    # Dedup (step 4).
    deduped = json.loads(_run("dedup", "ai", "--items-file", str(raw_file), "--mode", "annotate"))
    assert len(deduped) == 2
    opus = next(i for i in deduped if "Opus" in i["title"])
    assert opus["prior_coverage"][0]["source"] == "TechCrunch"

    # Framing (step 5) — simulate by merging why_it_matters.
    for i in deduped:
        i["why_it_matters"] = "matters because reasons"
    items_file = data_dir / "items.json"
    _write(items_file, deduped)

    # Assemble run.json (step 6).
    ts = "2026-06-29-0900"
    run_json_path = _run("assemble", "ai", ts, "--trigger", "run",
                         "--started-at", "2026-06-29T09:00:00",
                         "--items-file", str(items_file)).strip()
    run_obj = json.loads((data_dir / "briefs" / "ai" / ts / "run.json").read_text())
    assert run_obj["stats"] == {"items_total": 2, "items_new": 1, "items_prior": 1,
                                "sources_failed": 0}

    # Render (step 6 cont).
    _run("render", "ai", ts)
    out = brief_dir("ai", ts)
    html = (out / "brief.html").read_text()
    summary = (out / "summary.md").read_text()
    assert "Anthropic ships Opus 4.8" in html
    assert "matters because reasons" in summary

    # History (step 8).
    n = _run("history-from-run", "ai", ts).strip()
    assert n == "2"
    assert "Agent platform wars" in history_path("ai").read_text()

    # Podcast prompt (step 7).
    prompt = _run("podcast-prompt", "ai", ts)
    assert "two hosts" in prompt.lower()
    assert "ships LLM products" in prompt

    assert run_json_path.endswith("run.json")
