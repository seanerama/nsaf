"""Gemini idea generation provider."""

import json
import logging
import os

from google import genai
from google.genai import types

from prompt import build_prompt, TEMPERATURE_TIERS

log = logging.getLogger(__name__)


def generate(preferences, history_names, count=10):
    """Generate ideas using Gemini API with escalating temperature tiers."""
    client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
    all_ideas = []
    generated_names = []

    for temp, tier_count, label in TEMPERATURE_TIERS:
        prompt = build_prompt(preferences, history_names, tier_count, already_generated=generated_names)

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temp,
                    max_output_tokens=2000,
                ),
            )
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                text = text.rsplit("```", 1)[0].strip()

            raw_ideas = json.loads(text)
            for idea in raw_ideas[:tier_count]:
                idea["source"] = "gemini"
                idea["temperature"] = temp
                idea["tier"] = label
                all_ideas.append(idea)
                generated_names.append(idea["name"])
                log.info(f"Gemini [{label} t={temp}]: {idea['name']}")

        except Exception as e:
            log.error(f"Gemini tier {label} (t={temp}) failed: {e}")

    for i, idea in enumerate(all_ideas, 1):
        idea["rank"] = i

    return all_ideas
