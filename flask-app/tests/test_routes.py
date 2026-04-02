"""Tests for Flask routes and Webex commands."""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.db import (
    get_db, close_db, reset_db,
    ideas_insert_batch, project_create, project_get,
    queue_enqueue, queue_list, config_get, config_set,
    project_update,
)
from bot.commands import handle_command


SCHEMA = """
    CREATE TABLE IF NOT EXISTS ideas (
        id INTEGER PRIMARY KEY, date TEXT NOT NULL, source TEXT NOT NULL,
        rank INTEGER NOT NULL, name TEXT NOT NULL, description TEXT NOT NULL,
        category TEXT NOT NULL, complexity TEXT NOT NULL, suggested_stack TEXT,
        selected INTEGER DEFAULT 0, created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS idea_history (
        id INTEGER PRIMARY KEY, name TEXT NOT NULL,
        description TEXT NOT NULL, date TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY, idea_id INTEGER REFERENCES ideas(id),
        slug TEXT UNIQUE NOT NULL, status TEXT NOT NULL DEFAULT 'queued',
        port_start INTEGER, port_end INTEGER, db_name TEXT,
        project_dir TEXT NOT NULL, sdd_phase TEXT, sdd_active_role TEXT,
        sdd_progress INTEGER DEFAULT 0, deployed_url TEXT, render_url TEXT,
        last_state_change TEXT, stall_alerted INTEGER DEFAULT 0,
        started_at TEXT, completed_at TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS queue (
        id INTEGER PRIMARY KEY, project_id INTEGER REFERENCES projects(id),
        position INTEGER NOT NULL, created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS ports (
        port_start INTEGER PRIMARY KEY, port_end INTEGER NOT NULL,
        project_id INTEGER REFERENCES projects(id),
        allocated_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS config (
        key TEXT PRIMARY KEY, value TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_ideas_date ON ideas(date);
    CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
    CREATE INDEX IF NOT EXISTS idx_queue_position ON queue(position);
"""


@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    db = reset_db(db_path)
    db.executescript(SCHEMA)
    yield db
    close_db()


def _seed_ideas():
    ideas = [
        {"date": "2026-04-01", "source": "openai", "rank": i,
         "name": f"OpenAI App {i}", "description": f"Desc {i}",
         "category": "sports", "complexity": "medium", "suggested_stack": "{}"}
        for i in range(1, 4)
    ]
    ideas_insert_batch(ideas)


def _seed_project(slug="test-app", status="queued"):
    pid = project_create(slug, None, f"/tmp/{slug}")
    if status != "queued":
        project_update(slug, status=status)
    return pid


class TestWebexCommands:
    def test_status_empty(self):
        result = handle_command("status")
        assert "Nightshift AutoFoundry Status" in result
        assert "0" in result

    def test_status_with_projects(self):
        pid = _seed_project("my-app", "building")
        project_update("my-app", sdd_phase="design", sdd_active_role="Lead Architect")
        result = handle_command("status")
        assert "my-app" in result
        assert "1" in result

    def test_pause(self):
        result = handle_command("pause")
        assert "paused" in result.lower()
        assert config_get("paused") == "true"

    def test_resume(self):
        config_set("paused", "true")
        result = handle_command("resume")
        assert "resumed" in result.lower()
        assert config_get("paused") == "false"

    def test_skip_queued(self):
        pid = _seed_project("skip-me")
        queue_enqueue(pid)
        result = handle_command("skip skip-me")
        assert "scrapped" in result.lower()
        p = project_get("skip-me")
        assert p["status"] == "scrapped"

    def test_skip_not_found(self):
        result = handle_command("skip nonexistent")
        assert "not found" in result.lower()

    def test_skip_no_arg(self):
        result = handle_command("skip")
        assert "usage" in result.lower()

    def test_restart(self):
        pid = _seed_project("stalled-app", "building")
        project_update("stalled-app", stall_alerted=1)
        result = handle_command("restart stalled-app")
        assert "re-queued" in result.lower()
        p = project_get("stalled-app")
        assert p["status"] == "queued"
        assert p["stall_alerted"] == 0

    def test_promote_deployed(self):
        _seed_project("good-app", "deployed-local")
        result = handle_command("promote good-app")
        assert "promotion" in result.lower() or "promote" in result.lower()
        p = project_get("good-app")
        assert p["status"] == "promoted"

    def test_promote_wrong_status(self):
        _seed_project("queued-app")
        result = handle_command("promote queued-app")
        assert "can only promote" in result.lower()

    def test_help(self):
        result = handle_command("help")
        assert "status" in result
        assert "pause" in result
        assert "promote" in result

    def test_unknown_command(self):
        result = handle_command("foobar")
        assert "unknown" in result.lower()


class TestFlaskApp:
    @pytest.fixture
    def client(self, fresh_db):
        os.environ["NSAF_DB_PATH"] = fresh_db.execute("PRAGMA database_list").fetchone()[2]
        from app import app
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

    def test_select_page_loads(self, client):
        resp = client.get("/select")
        assert resp.status_code == 200
        assert b"NSAF" in resp.data

    def test_select_with_ideas(self, client):
        _seed_ideas()
        resp = client.get("/select?date=2026-04-01")
        assert resp.status_code == 200
        assert b"OpenAI App 1" in resp.data

    def test_review_not_found(self, client):
        resp = client.get("/review/nonexistent")
        assert resp.status_code == 404

    def test_review_page_loads(self, client):
        _seed_project("review-app", "deployed-local")
        resp = client.get("/review/review-app")
        assert resp.status_code == 200
        assert b"review-app" in resp.data

    def test_404_handler(self, client):
        resp = client.get("/nonexistent-page")
        assert resp.status_code == 404
