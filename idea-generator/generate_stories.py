#!/usr/bin/env python3
"""NSAF Story Idea Generator — produces children's story seed ideas.

Usage:
    python generate_stories.py             # Generate stories, store in DB
    python generate_stories.py --dry-run   # Print to stdout, no side effects
    python generate_stories.py --count 20  # Override per-provider idea count
"""

import argparse
import json
import logging
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

from shared.config import load_story_preferences
from shared.db import close_db, story_ideas_init, story_ideas_insert_batch

from dedup import get_story_history_names, record_story_ideas
from prompt import build_story_prompt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
log = logging.getLogger("nsaf.generate_stories")


def generate_all(preferences, history_names, count):
    """Run every available provider with the story prompt builder."""
    all_ideas = []
    providers = []

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
        log.info(f"Generating story ideas from {name}...")
        try:
            ideas = gen_func(
                preferences,
                history_names,
                count=count,
                prompt_builder=build_story_prompt,
            )
            log.info(f"{name}: got {len(ideas)} story ideas")
            all_ideas.extend(ideas)
        except Exception as e:
            log.error(f"{name} provider failed completely: {e}")

    return all_ideas


def store(ideas, today):
    rows = []
    for idea in ideas:
        themes = idea.get("themes")
        if isinstance(themes, list):
            themes = json.dumps(themes)
        rows.append({
            "date": today,
            "source": idea.get("source", "unknown"),
            "rank": idea.get("rank", 0),
            "name": idea["name"],
            "description": idea["description"],
            "target_age": idea.get("target_age"),
            "length_minutes": idea.get("length_minutes"),
            "art_style_hint": idea.get("art_style_hint"),
            "themes": themes,
            "temperature": idea.get("temperature", 0),
            "tier": idea.get("tier", "unknown"),
        })
    if rows:
        story_ideas_insert_batch(rows)
        log.info(f"Stored {len(rows)} story ideas in SQLite")


def main():
    parser = argparse.ArgumentParser(description="NSAF Story Idea Generator")
    parser.add_argument("--dry-run", action="store_true", help="Print ideas without storing")
    parser.add_argument(
        "--count", type=int, default=10,
        help="Per-provider idea count (default 10, scaled across temperature tiers)",
    )
    args = parser.parse_args()

    today = date.today().isoformat()
    log.info(f"Starting story idea generation for {today}")

    prefs_path = os.environ.get("NSAF_STORY_PREFERENCES_PATH", "./story-preferences.md")
    preferences = load_story_preferences(prefs_path)
    log.info(
        f"Loaded story preferences: {len(preferences['themes'])} themes, "
        f"{len(preferences['settings'])} settings"
    )

    history_names = []
    if not args.dry_run:
        story_ideas_init()
        history_names = get_story_history_names()

    ideas = generate_all(preferences, history_names, count=args.count)
    log.info(f"Total story ideas generated: {len(ideas)}")

    if args.dry_run:
        print(json.dumps(ideas, indent=2))
        return

    if not ideas:
        log.warning("No story ideas generated — nothing to store")
        return

    store(ideas, today)
    record_story_ideas(ideas, today)

    log.info("Story idea generation complete")
    close_db()


if __name__ == "__main__":
    main()
