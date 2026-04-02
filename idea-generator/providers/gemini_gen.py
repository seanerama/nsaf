"""Gemini idea generation provider."""

import json
import logging

import google.generativeai as genai

from prompt import build_prompt, get_temperature

log = logging.getLogger(__name__)


def generate(preferences, history_names, count=10):
    """Generate ideas using Gemini API with escalating temperature."""
    ideas = []

    for rank in range(1, count + 1):
        temp = get_temperature(rank)
        prompt = build_prompt(preferences, history_names, rank)

        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temp,
                    max_output_tokens=500,
                ),
            )
            text = response.text.strip()
            idea = json.loads(text)
            idea["rank"] = rank
            idea["source"] = "gemini"
            ideas.append(idea)
            log.info(f"Gemini rank {rank} (temp={temp}): {idea['name']}")
        except Exception as e:
            log.error(f"Gemini rank {rank} failed: {e}")
            continue

    return ideas
