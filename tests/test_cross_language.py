"""Cross-language integration test: verify Node.js and Python share SQLite correctly."""

import os
import sys
import subprocess
import tempfile
import sqlite3
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.db import (
    reset_db, close_db, get_db,
    ideas_insert, ideas_for_date,
    project_create, project_get,
    config_set, config_get,
)


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
"""


@pytest.fixture
def shared_db(tmp_path):
    db_path = str(tmp_path / "cross_test.db")
    db = reset_db(db_path)
    db.executescript(SCHEMA)
    yield db_path
    close_db()


class TestCrossLanguage:
    def test_python_writes_node_reads(self, shared_db):
        """Python writes an idea, Node.js reads it."""
        # Python writes
        idea_id = ideas_insert({
            "date": "2026-04-01", "source": "openai", "rank": 1,
            "name": "CrossTest App", "description": "Testing cross-lang",
            "category": "testing", "complexity": "low", "suggested_stack": "{}",
        })
        assert idea_id > 0

        # Node.js reads
        node_script = f"""
        import Database from 'better-sqlite3';
        const db = new Database('{shared_db}');
        db.pragma('journal_mode = WAL');
        const row = db.prepare('SELECT * FROM ideas WHERE id = ?').get({idea_id});
        if (row && row.name === 'CrossTest App') {{
            console.log('OK');
        }} else {{
            console.log('FAIL');
            process.exit(1);
        }}
        db.close();
        """
        result = subprocess.run(
            ["node", "--input-type=module", "-e", node_script],
            capture_output=True, text=True,
            cwd=os.path.join(os.path.dirname(__file__), "..", "orchestrator"),
            timeout=10,
        )
        assert result.stdout.strip() == "OK", f"Node stdout: {result.stdout}, stderr: {result.stderr}"

    def test_node_writes_python_reads(self, shared_db):
        """Node.js writes a project, Python reads it."""
        node_script = f"""
        import Database from 'better-sqlite3';
        const db = new Database('{shared_db}');
        db.pragma('journal_mode = WAL');
        db.prepare("INSERT INTO projects (slug, project_dir) VALUES (?, ?)").run('node-written-app', '/tmp/node-app');
        console.log('OK');
        db.close();
        """
        result = subprocess.run(
            ["node", "--input-type=module", "-e", node_script],
            capture_output=True, text=True,
            cwd=os.path.join(os.path.dirname(__file__), "..", "orchestrator"),
            timeout=10,
        )
        assert result.stdout.strip() == "OK", f"Node write failed: {result.stderr}"

        # Python reads
        project = project_get("node-written-app")
        assert project is not None
        assert project["slug"] == "node-written-app"
        assert project["status"] == "queued"

    def test_concurrent_config_access(self, shared_db):
        """Both sides can read/write config without corruption."""
        # Python writes
        config_set("python_key", "python_value")

        # Node.js writes and reads
        node_script = f"""
        import Database from 'better-sqlite3';
        const db = new Database('{shared_db}');
        db.pragma('journal_mode = WAL');
        db.pragma('busy_timeout = 5000');

        // Read Python's value
        const pyVal = db.prepare("SELECT value FROM config WHERE key = 'python_key'").get();
        if (!pyVal || pyVal.value !== 'python_value') {{
            console.log('FAIL_READ');
            process.exit(1);
        }}

        // Write Node's value
        db.prepare("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)").run('node_key', 'node_value');
        console.log('OK');
        db.close();
        """
        result = subprocess.run(
            ["node", "--input-type=module", "-e", node_script],
            capture_output=True, text=True,
            cwd=os.path.join(os.path.dirname(__file__), "..", "orchestrator"),
            timeout=10,
        )
        assert result.stdout.strip() == "OK", f"Node: {result.stderr}"

        # Python reads Node's value
        assert config_get("node_key") == "node_value"

    def test_wal_mode_enabled(self, shared_db):
        """Both connections use WAL mode."""
        db = get_db()
        mode = db.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"

        # Verify Node sees WAL too
        node_script = f"""
        import Database from 'better-sqlite3';
        const db = new Database('{shared_db}');
        const mode = db.pragma('journal_mode', {{ simple: true }});
        console.log(mode);
        db.close();
        """
        result = subprocess.run(
            ["node", "--input-type=module", "-e", node_script],
            capture_output=True, text=True,
            cwd=os.path.join(os.path.dirname(__file__), "..", "orchestrator"),
            timeout=10,
        )
        assert result.stdout.strip() == "wal"
