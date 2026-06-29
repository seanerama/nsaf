#!/usr/bin/env python3
"""NSAF Techguide Idea Generator — produces technical-guide topic ideas.

Usage:
    python generate_techguides.py             # Generate techguides, store in DB
    python generate_techguides.py --dry-run   # Print to stdout, no side effects
    python generate_techguides.py --count 5   # Override per-provider idea count

A techguide is a self-contained piece of web content for seanmahoney.ai/guides.
The model picks one of three variants per idea: 'interactive', 'comparison', or
'explainer'.
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

from shared.config import load_techguide_preferences
from shared.db import close_db, techguide_ideas_init, techguide_ideas_insert_batch

from dedup import get_techguide_history_names, record_techguide_ideas
from prompt import build_techguide_prompt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
log = logging.getLogger("nsaf.generate_techguides")


def generate_all(preferences, history_names, count):
    """Run every available provider with the techguide prompt builder."""
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
        log.info(f"Generating techguide ideas from {name}...")
        try:
            ideas = gen_func(
                preferences,
                history_names,
                count=count,
                prompt_builder=build_techguide_prompt,
            )
            log.info(f"{name}: got {len(ideas)} techguide ideas")
            all_ideas.extend(ideas)
        except Exception as e:
            log.error(f"{name} provider failed completely: {e}")

    return all_ideas


def store(ideas, today):
    rows = []
    for idea in ideas:
        products = idea.get("products")
        if isinstance(products, list):
            products = json.dumps(products)
        rows.append({
            "date": today,
            "source": idea.get("source", "unknown"),
            "rank": idea.get("rank", 0),
            "name": idea["name"],
            "description": idea["description"],
            "variant": idea.get("variant", "interactive"),
            "level": idea.get("level"),
            "suggested_source_url": idea.get("suggested_source_url"),
            "products": products,
            "temperature": idea.get("temperature", 0),
            "tier": idea.get("tier", "unknown"),
        })
    if rows:
        techguide_ideas_insert_batch(rows)
        log.info(f"Stored {len(rows)} techguide ideas in SQLite")


def main():
    parser = argparse.ArgumentParser(description="NSAF Techguide Idea Generator")
    parser.add_argument("--dry-run", action="store_true", help="Print ideas without storing")
    parser.add_argument(
        "--count", type=int, default=None,
        help="Per-provider idea count (default from preferences on-demand quota)",
    )
    args = parser.parse_args()

    today = date.today().isoformat()
    log.info(f"Starting techguide idea generation for {today}")

    prefs_path = os.environ.get("NSAF_TECHGUIDE_PREFERENCES_PATH", "./techguide-preferences.md")
    preferences = load_techguide_preferences(prefs_path)
    count = args.count if args.count is not None else preferences.get("on_demand_quota", 5)
    log.info(
        f"Loaded techguide preferences: {len(preferences['subject_domains'])} domains, "
        f"levels {preferences['levels']['min']}->{preferences['levels']['max']}, "
        f"count={count}"
    )

    history_names = []
    if not args.dry_run:
        techguide_ideas_init()
        history_names = get_techguide_history_names()

    ideas = generate_all(preferences, history_names, count=count)
    log.info(f"Total techguide ideas generated: {len(ideas)}")

    if args.dry_run:
        print(json.dumps(ideas, indent=2))
        return

    if not ideas:
        log.warning("No techguide ideas generated — nothing to store")
        return

    store(ideas, today)
    record_techguide_ideas(ideas, today)

    log.info("Techguide idea generation complete")
    close_db()


if __name__ == "__main__":
    main()
