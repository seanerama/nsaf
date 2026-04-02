"""OpenAI idea generation provider."""

import json
import logging

from openai import OpenAI

from prompt import build_prompt, get_temperature

log = logging.getLogger(__name__)


def generate(preferences, history_names, count=10):
    """Generate ideas using OpenAI API with escalating temperature."""
    client = OpenAI()
    ideas = []

    for rank in range(1, count + 1):
        temp = get_temperature(rank)
        prompt = build_prompt(preferences, history_names, rank)

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=temp,
                max_tokens=500,
            )
            text = response.choices[0].message.content.strip()
            idea = json.loads(text)
            idea["rank"] = rank
            idea["source"] = "openai"
            ideas.append(idea)
            log.info(f"OpenAI rank {rank} (temp={temp}): {idea['name']}")
        except Exception as e:
            log.error(f"OpenAI rank {rank} failed: {e}")
            continue

    return ideas
