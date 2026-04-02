"""Tests for idea generator modules."""

import json
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from prompt import build_prompt, get_temperature, TEMPERATURES
from email_sender import format_ideas_html
from dedup import get_history_names, record_ideas
from shared.db import (
    get_db, close_db, reset_db,
    history_all, history_insert_batch,
    ideas_insert_batch, ideas_for_date,
)


@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    db = reset_db(db_path)
    db.executescript("""
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
        CREATE INDEX IF NOT EXISTS idx_ideas_date ON ideas(date);
    """)
    yield db
    close_db()


SAMPLE_PREFS = {
    "categories": ["sports", "fitness", "education"],
    "exclusions": ["gambling"],
    "tech_stack": {"frontend": "React", "backend": "Node.js", "database": "PostgreSQL", "css": "Tailwind"},
    "complexity_range": {"min": "medium", "max": "high"},
    "design": {"tone": "modern, clean", "mobile_first": True},
}


class TestPrompt:
    def test_build_prompt_includes_categories(self):
        prompt = build_prompt(SAMPLE_PREFS, [], 1)
        assert "sports" in prompt
        assert "fitness" in prompt
        assert "education" in prompt

    def test_build_prompt_includes_exclusions(self):
        prompt = build_prompt(SAMPLE_PREFS, [], 1)
        assert "gambling" in prompt

    def test_build_prompt_includes_stack(self):
        prompt = build_prompt(SAMPLE_PREFS, [], 1)
        assert "React" in prompt
        assert "Node.js" in prompt

    def test_build_prompt_includes_history(self):
        prompt = build_prompt(SAMPLE_PREFS, ["Old App", "Past App"], 1)
        assert "Old App" in prompt
        assert "Past App" in prompt

    def test_build_prompt_creativity_low_rank(self):
        prompt = build_prompt(SAMPLE_PREFS, [], 1)
        assert "practical and grounded" in prompt

    def test_build_prompt_creativity_mid_rank(self):
        prompt = build_prompt(SAMPLE_PREFS, [], 5)
        assert "moderately creative" in prompt

    def test_build_prompt_creativity_high_rank(self):
        prompt = build_prompt(SAMPLE_PREFS, [], 8)
        assert "creative and experimental" in prompt

    def test_prompt_requests_json(self):
        prompt = build_prompt(SAMPLE_PREFS, [], 1)
        assert '"name"' in prompt
        assert '"description"' in prompt

    def test_no_history_no_exclusion_block(self):
        prompt = build_prompt(SAMPLE_PREFS, [], 1)
        assert "Do NOT suggest" not in prompt


class TestTemperature:
    def test_temperatures_length(self):
        assert len(TEMPERATURES) == 10

    def test_temperatures_ascending(self):
        for i in range(len(TEMPERATURES) - 1):
            assert TEMPERATURES[i] < TEMPERATURES[i + 1]

    def test_get_temperature_valid(self):
        assert get_temperature(1) == 0.3
        assert get_temperature(10) == 1.2

    def test_get_temperature_out_of_range(self):
        assert get_temperature(0) == 0.7
        assert get_temperature(11) == 0.7


class TestDedup:
    def test_get_history_empty(self):
        names = get_history_names()
        assert names == []

    def test_record_and_get(self):
        ideas = [
            {"name": "App A", "description": "Desc A"},
            {"name": "App B", "description": "Desc B"},
        ]
        record_ideas(ideas, "2026-04-01")
        names = get_history_names()
        assert "App A" in names
        assert "App B" in names

    def test_record_empty(self):
        record_ideas([], "2026-04-01")
        assert get_history_names() == []


class TestEmail:
    def test_format_groups_by_provider(self):
        ideas = [
            {"name": "OAI App", "description": "d", "source": "openai", "rank": 1, "category": "sports", "complexity": "medium", "suggested_stack": {}},
            {"name": "Gem App", "description": "d", "source": "gemini", "rank": 1, "category": "fitness", "complexity": "high", "suggested_stack": {}},
            {"name": "Ant App", "description": "d", "source": "anthropic", "rank": 1, "category": "education", "complexity": "low", "suggested_stack": {}},
        ]
        html = format_ideas_html(ideas, "http://localhost:5000/select")
        assert "OpenAI" in html
        assert "Gemini" in html
        assert "Anthropic" in html
        assert "OAI App" in html
        assert "Gem App" in html
        assert "Ant App" in html

    def test_format_includes_selection_link(self):
        html = format_ideas_html([], "http://myserver:5000/select")
        assert "http://myserver:5000/select" in html

    def test_format_handles_string_stack(self):
        ideas = [
            {"name": "Test", "description": "d", "source": "openai", "rank": 1,
             "category": "sports", "complexity": "medium",
             "suggested_stack": '{"frontend": "React"}'},
        ]
        html = format_ideas_html(ideas, "http://localhost:5000/select")
        assert "React" in html

    def test_format_shows_idea_count(self):
        ideas = [
            {"name": f"App {i}", "description": "d", "source": "openai", "rank": i,
             "category": "sports", "complexity": "medium", "suggested_stack": {}}
            for i in range(1, 6)
        ]
        html = format_ideas_html(ideas, "http://localhost:5000/select")
        assert "5 app ideas" in html.lower() or "5" in html
