"""OpenAI idea generation provider."""

import json
import logging

from openai import OpenAI

from prompt import build_prompt, TEMPERATURE_TIERS

log = logging.getLogger(__name__)


def generate(preferences, history_names, count=10):
    """Generate ideas using OpenAI API with escalating temperature tiers."""
    client = OpenAI()
    tiers = TEMPERATURE_TIERS.get("openai", TEMPERATURE_TIERS["openai"])
    all_ideas = []
    generated_names = []

    for temp, tier_count, label in tiers:
        prompt = build_prompt(preferences, history_names, tier_count, already_generated=generated_names)

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=temp,
                max_tokens=2000,
            )
            text = response.choices[0].message.content.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                text = text.rsplit("```", 1)[0].strip()

            raw_ideas = json.loads(text)
            for idea in raw_ideas[:tier_count]:
                idea["source"] = "openai"
                idea["temperature"] = temp
                idea["tier"] = label
                all_ideas.append(idea)
                generated_names.append(idea["name"])
                log.info(f"OpenAI [{label} t={temp}]: {idea['name']}")

        except Exception as e:
            log.error(f"OpenAI tier {label} (t={temp}) failed: {e}")

    # Assign rank based on final order
    for i, idea in enumerate(all_ideas, 1):
        idea["rank"] = i

    return all_ideas
