"""Anthropic idea generation provider."""

import json
import logging

from anthropic import Anthropic

from prompt import build_prompt, get_temperature

log = logging.getLogger(__name__)


def generate(preferences, history_names, count=10):
    """Generate ideas using Anthropic API with escalating temperature."""
    client = Anthropic()
    ideas = []

    for rank in range(1, count + 1):
        temp = get_temperature(rank)
        prompt = build_prompt(preferences, history_names, rank)

        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=500,
                temperature=temp,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                text = text.rsplit("```", 1)[0].strip()
            idea = json.loads(text)
            idea["rank"] = rank
            idea["source"] = "anthropic"
            ideas.append(idea)
            log.info(f"Anthropic rank {rank} (temp={temp}): {idea['name']}")
        except Exception as e:
            log.error(f"Anthropic rank {rank} failed: {e}")
            continue

    return ideas
