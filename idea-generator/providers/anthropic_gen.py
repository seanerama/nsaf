"""Anthropic idea generation provider."""

import json
import logging

from anthropic import Anthropic

from prompt import build_prompt, TEMPERATURE_TIERS, scale_tiers

log = logging.getLogger(__name__)


def generate(preferences, history_names, count=10, prompt_builder=None):
    """Generate ideas using Anthropic API with escalating temperature tiers.

    prompt_builder is a callable (preferences, history_names, count, already_generated)
    -> str. Defaults to the apps prompt for backwards compatibility.
    """
    if prompt_builder is None:
        prompt_builder = build_prompt
    client = Anthropic()
    tiers = TEMPERATURE_TIERS.get("anthropic", TEMPERATURE_TIERS["openai"])
    tiers = scale_tiers(tiers, count)
    all_ideas = []
    generated_names = []

    for temp, tier_count, label in tiers:
        prompt = prompt_builder(preferences, history_names, tier_count, already_generated=generated_names)

        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2000,
                temperature=temp,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                text = text.rsplit("```", 1)[0].strip()

            raw_ideas = json.loads(text)
            for idea in raw_ideas[:tier_count]:
                idea["source"] = "anthropic"
                idea["temperature"] = temp
                idea["tier"] = label
                all_ideas.append(idea)
                generated_names.append(idea["name"])
                log.info(f"Anthropic [{label} t={temp}]: {idea['name']}")

        except Exception as e:
            log.error(f"Anthropic tier {label} (t={temp}) failed: {e}")

    for i, idea in enumerate(all_ideas, 1):
        idea["rank"] = i

    return all_ideas
