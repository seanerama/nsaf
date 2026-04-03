#!/usr/bin/env python3
"""NSAF Morning Idea Generator — cron entry point.

Usage:
    python generate.py              # Generate ideas, store, and email
    python generate.py --dry-run    # Print ideas to stdout, no side effects
"""

import argparse
import json
import logging
import os
import sys
from datetime import date

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

from shared.config import load_preferences
from shared.db import get_db, close_db, ideas_insert_batch

from dedup import get_history_names, record_ideas
from email_sender import send_morning_email

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
log = logging.getLogger("nsaf.generate")


def init_db_for_generator():
    """Ensure DB is initialized for the generator."""
    db = get_db()
    # Schema should already exist from orchestrator init,
    # but create tables if running standalone
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
            temperature REAL,
            tier TEXT,
            selected INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS idea_history (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            date TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_ideas_date ON ideas(date);
    """)
    return db


def generate_all_ideas(preferences, history_names, dry_run=False):
    """Generate ideas from all 3 providers. Returns list of idea dicts."""
    all_ideas = []
    providers = []

    # Import providers — each one is optional (API key may not be set)
    try:
        from providers.openai_gen import generate as openai_gen
        providers.append(("openai", openai_gen))
    except ImportError as e:
        log.warning(f"OpenAI provider unavailable: {e}")

    try:
        from providers.gemini_gen import generate as gemini_gen
        providers.append(("gemini", gemini_gen))
    except ImportError as e:
        log.warning(f"Gemini provider unavailable: {e}")

    try:
        from providers.anthropic_gen import generate as anthropic_gen
        providers.append(("anthropic", anthropic_gen))
    except ImportError as e:
        log.warning(f"Anthropic provider unavailable: {e}")

    for name, gen_func in providers:
        log.info(f"Generating ideas from {name}...")
        try:
            ideas = gen_func(preferences, history_names, count=10)
            log.info(f"{name}: got {len(ideas)} ideas")
            all_ideas.extend(ideas)
        except Exception as e:
            log.error(f"{name} provider failed completely: {e}")

    return all_ideas


def store_ideas(ideas, today):
    """Write ideas to SQLite."""
    rows = []
    for idea in ideas:
        stack = idea.get("suggested_stack", {})
        if isinstance(stack, dict):
            stack = json.dumps(stack)
        rows.append({
            "date": today,
            "source": idea.get("source", "unknown"),
            "rank": idea.get("rank", 0),
            "name": idea["name"],
            "description": idea["description"],
            "category": idea.get("category", "uncategorized"),
            "complexity": idea.get("complexity", "medium"),
            "suggested_stack": stack,
            "temperature": idea.get("temperature", 0),
            "tier": idea.get("tier", "unknown"),
        })
    if rows:
        ideas_insert_batch(rows)
        log.info(f"Stored {len(rows)} ideas in SQLite")


def main():
    parser = argparse.ArgumentParser(description="NSAF Morning Idea Generator")
    parser.add_argument("--dry-run", action="store_true", help="Print ideas without storing or emailing")
    args = parser.parse_args()

    today = date.today().isoformat()
    log.info(f"Starting idea generation for {today}")

    # Load preferences
    prefs_path = os.environ.get("NSAF_PREFERENCES_PATH", "./preferences.md")
    preferences = load_preferences(prefs_path)
    log.info(f"Loaded preferences: {len(preferences['categories'])} categories")

    if not args.dry_run:
        init_db_for_generator()

    # Load history for dedup
    history_names = []
    if not args.dry_run:
        history_names = get_history_names()

    # Generate
    ideas = generate_all_ideas(preferences, history_names, dry_run=args.dry_run)
    log.info(f"Total ideas generated: {len(ideas)}")

    if args.dry_run:
        print(json.dumps(ideas, indent=2))
        return

    if not ideas:
        log.warning("No ideas generated — nothing to store or email")
        return

    # Store in SQLite
    store_ideas(ideas, today)

    # Record in history for future dedup
    record_ideas(ideas, today)

    # Send morning email
    flask_host = os.environ.get("NSAF_FLASK_HOST", "localhost")
    flask_port = os.environ.get("NSAF_FLASK_PORT", "5000")
    selection_url = f"http://{flask_host}:{flask_port}/select"
    send_morning_email(ideas, selection_url)

    log.info("Idea generation complete")
    close_db()


if __name__ == "__main__":
    main()
