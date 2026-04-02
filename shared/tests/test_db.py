import os
import tempfile
import pytest

from shared.db import (
    get_db, close_db, reset_db,
    ideas_insert, ideas_insert_batch, ideas_for_date, idea_get,
    history_insert, history_insert_batch, history_all,
    project_create, project_update, project_get, projects_by_status,
    queue_enqueue, queue_remove, queue_list,
    config_get, config_set,
)


@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    db = reset_db(db_path)
    # Create schema
    db.executescript("""
        CREATE TABLE IF NOT EXISTS ideas (
            id INTEGER PRIMARY KEY,
            date TEXT NOT NULL,
            source TEXT NOT NULL,
            rank INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            complexity TEXT NOT NULL,
            suggested_stack TEXT,
            selected INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS idea_history (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            date TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY,
            idea_id INTEGER REFERENCES ideas(id),
            slug TEXT UNIQUE NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued',
            port_start INTEGER,
            port_end INTEGER,
            db_name TEXT,
            project_dir TEXT NOT NULL,
            sdd_phase TEXT,
            sdd_active_role TEXT,
            sdd_progress INTEGER DEFAULT 0,
            deployed_url TEXT,
            render_url TEXT,
            last_state_change TEXT,
            stall_alerted INTEGER DEFAULT 0,
            started_at TEXT,
            completed_at TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS queue (
            id INTEGER PRIMARY KEY,
            project_id INTEGER REFERENCES projects(id),
            position INTEGER NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS ports (
            port_start INTEGER PRIMARY KEY,
            port_end INTEGER NOT NULL,
            project_id INTEGER REFERENCES projects(id),
            allocated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_ideas_date ON ideas(date);
        CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
        CREATE INDEX IF NOT EXISTS idx_queue_position ON queue(position);
    """)
    yield db
    close_db()


class TestIdeas:
    def test_insert_and_get(self):
        idea = {
            "date": "2026-04-01",
            "source": "openai",
            "rank": 1,
            "name": "Fitness Tracker",
            "description": "Track workouts",
            "category": "fitness",
            "complexity": "medium",
            "suggested_stack": '{"frontend": "React"}',
        }
        idea_id = ideas_insert(idea)
        assert idea_id > 0

        fetched = idea_get(idea_id)
        assert fetched["name"] == "Fitness Tracker"
        assert fetched["source"] == "openai"

    def test_insert_batch(self):
        ideas = [
            {
                "date": "2026-04-01", "source": "gemini", "rank": i,
                "name": f"App {i}", "description": f"Desc {i}",
                "category": "productivity", "complexity": "low",
                "suggested_stack": None,
            }
            for i in range(1, 11)
        ]
        ideas_insert_batch(ideas)
        fetched = ideas_for_date("2026-04-01")
        assert len(fetched) == 10

    def test_ideas_for_date_empty(self):
        assert ideas_for_date("2099-01-01") == []

    def test_idea_get_missing(self):
        assert idea_get(99999) is None


class TestIdeaHistory:
    def test_insert_and_list(self):
        history_insert("Old App", "An old app", "2026-03-01")
        items = history_all()
        assert len(items) == 1
        assert items[0]["name"] == "Old App"

    def test_insert_batch(self):
        batch = [
            {"name": f"Past {i}", "description": f"Desc {i}", "date": "2026-03-01"}
            for i in range(5)
        ]
        history_insert_batch(batch)
        assert len(history_all()) == 5


class TestProjects:
    def test_create_and_get(self):
        pid = project_create("my-app", None, "/tmp/my-app")
        assert pid > 0
        p = project_get("my-app")
        assert p["slug"] == "my-app"
        assert p["status"] == "queued"

    def test_get_missing(self):
        assert project_get("nonexistent") is None

    def test_update(self):
        project_create("upd-app", None, "/tmp/upd")
        project_update("upd-app", status="building", sdd_phase="design")
        p = project_get("upd-app")
        assert p["status"] == "building"
        assert p["sdd_phase"] == "design"

    def test_by_status(self):
        project_create("s1", None, "/tmp/s1")
        project_create("s2", None, "/tmp/s2")
        project_update("s1", status="building")
        building = projects_by_status("building")
        assert any(p["slug"] == "s1" for p in building)
        queued = projects_by_status("queued")
        assert any(p["slug"] == "s2" for p in queued)


class TestQueue:
    def test_enqueue_and_list(self):
        pid1 = project_create("qa1", None, "/tmp/qa1")
        pid2 = project_create("qa2", None, "/tmp/qa2")
        queue_enqueue(pid1)
        queue_enqueue(pid2)
        q = queue_list()
        assert len(q) == 2
        assert q[0]["slug"] == "qa1"
        assert q[1]["slug"] == "qa2"

    def test_remove(self):
        pid = project_create("qr1", None, "/tmp/qr1")
        queue_enqueue(pid)
        queue_remove(pid)
        assert queue_list() == []


class TestConfig:
    def test_get_missing(self):
        assert config_get("missing") is None

    def test_set_and_get(self):
        config_set("key1", "val1")
        assert config_get("key1") == "val1"

    def test_overwrite(self):
        config_set("key2", "a")
        config_set("key2", "b")
        assert config_get("key2") == "b"
