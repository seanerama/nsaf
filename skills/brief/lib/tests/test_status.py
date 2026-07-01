"""Stage 6: status report reflects profiles, history, and last runs."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from daily_brief.cli import app
from daily_brief.paths import brief_dir
from daily_brief.status import gather_status

runner = CliRunner()


def _run(*args):
    result = runner.invoke(app, list(args))
    assert result.exit_code == 0, result.output
    return result.output


def test_status_empty(data_dir):
    report = gather_status()
    assert report["totals"] == {"profiles": 0, "history_entries": 0, "runs": 0}


def test_status_reflects_profiles_history_and_runs(data_dir):
    _run("init")  # general profile
    _run("profile", "create", "ai", "--title", "AI", "--description", "d", "--from-sample")

    # Add history for ai.
    hist = [{"date": "2026-06-29", "topic": "t", "title": "x", "source": "s",
             "url": None, "dedup_key": "k1"}]
    hf = data_dir / "h.json"
    hf.write_text(json.dumps(hist), encoding="utf-8")
    _run("history", "add", "ai", "--json-file", str(hf))

    # Create a run for ai.
    ts = "2026-06-29-1000"
    run_dir = brief_dir("ai", ts)
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run.json").write_text(json.dumps({
        "profile": "ai", "trigger": "run", "started_at": "2026-06-29T10:00:00",
        "items": [], "failures": [], "stats": {"items_total": 3, "items_new": 2},
    }), encoding="utf-8")

    report = gather_status()
    ai = next(p for p in report["profiles"] if p["slug"] == "ai")
    assert ai["history_entries"] == 1
    assert ai["topics"] >= 2
    assert ai["runs"] == 1
    assert ai["last_run"]["timestamp"] == ts
    assert ai["last_run"]["stats"]["items_total"] == 3
    assert report["totals"]["profiles"] == 2

    out = json.loads(_run("status", "--json"))
    assert out["totals"]["runs"] == 1
    assert any(p["slug"] == "ai" for p in out["profiles"])


def test_status_text_output(data_dir):
    _run("init")
    out = _run("status")
    assert "general" in out
    assert "Totals:" in out
