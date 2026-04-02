"""Anthropic idea generation provider."""

import json
import logging

from anthropic import Anthropic

from prompt import build_prompt, DEFAULT_TEMPERATURE

log = logging.getLogger(__name__)


def generate(preferences, history_names, count=10):
    """Generate ideas using Anthropic API — single call for all ideas."""
    client = Anthropic()
    prompt = build_prompt(preferences, history_names, count)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4000,
            temperature=DEFAULT_TEMPERATURE,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0].strip()

        raw_ideas = json.loads(text)
        ideas = []
        for i, idea in enumerate(raw_ideas[:count], 1):
            idea["rank"] = i
            idea["source"] = "anthropic"
            ideas.append(idea)
            log.info(f"Anthropic idea {i}: {idea['name']}")

        return ideas
    except Exception as e:
        log.error(f"Anthropic generation failed: {e}")
        return []
