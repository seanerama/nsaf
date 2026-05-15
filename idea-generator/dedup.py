"""Idea history and deduplication."""

import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.db import (
    history_all, history_insert_batch,
    story_history_all, story_history_insert_batch,
    study_history_all, study_history_insert_batch,
)

log = logging.getLogger(__name__)


def get_history_names():
    """Load all past idea names for exclusion from prompts."""
    history = history_all()
    names = [item["name"] for item in history]
    log.info(f"Loaded {len(names)} past idea names for dedup")
    return names


def record_ideas(ideas, date):
    """Record new ideas in history for future dedup."""
    items = [
        {"name": idea["name"], "description": idea["description"], "date": date}
        for idea in ideas
    ]
    if items:
        history_insert_batch(items)
        log.info(f"Recorded {len(items)} ideas to history")


def get_story_history_names():
    history = story_history_all()
    names = [item["name"] for item in history]
    log.info(f"Loaded {len(names)} past story idea names for dedup")
    return names


def record_story_ideas(ideas, date):
    items = [
        {"name": idea["name"], "description": idea["description"], "date": date}
        for idea in ideas
    ]
    if items:
        story_history_insert_batch(items)
        log.info(f"Recorded {len(items)} story ideas to history")


def get_study_history_names():
    history = study_history_all()
    names = [item["name"] for item in history]
    log.info(f"Loaded {len(names)} past study idea names for dedup")
    return names


def record_study_ideas(ideas, date):
    items = [
        {"name": idea["name"], "description": idea["description"], "date": date}
        for idea in ideas
    ]
    if items:
        study_history_insert_batch(items)
        log.info(f"Recorded {len(items)} study ideas to history")
