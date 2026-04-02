"""OpenAI idea generation provider."""

import json
import logging

from openai import OpenAI

from prompt import build_prompt, DEFAULT_TEMPERATURE

log = logging.getLogger(__name__)


def generate(preferences, history_names, count=10):
    """Generate ideas using OpenAI API — single call for all ideas."""
    client = OpenAI()
    prompt = build_prompt(preferences, history_names, count)

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=DEFAULT_TEMPERATURE,
            max_tokens=4000,
        )
        text = response.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0].strip()

        raw_ideas = json.loads(text)
        ideas = []
        for i, idea in enumerate(raw_ideas[:count], 1):
            idea["rank"] = i
            idea["source"] = "openai"
            ideas.append(idea)
            log.info(f"OpenAI idea {i}: {idea['name']}")

        return ideas
    except Exception as e:
        log.error(f"OpenAI generation failed: {e}")
        return []
