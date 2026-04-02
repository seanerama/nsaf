"""Gemini idea generation provider."""

import json
import logging

import google.generativeai as genai

from prompt import build_prompt, DEFAULT_TEMPERATURE

log = logging.getLogger(__name__)


def generate(preferences, history_names, count=10):
    """Generate ideas using Gemini API — single call for all ideas."""
    prompt = build_prompt(preferences, history_names, count)

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=DEFAULT_TEMPERATURE,
                max_output_tokens=4000,
            ),
        )
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0].strip()

        raw_ideas = json.loads(text)
        ideas = []
        for i, idea in enumerate(raw_ideas[:count], 1):
            idea["rank"] = i
            idea["source"] = "gemini"
            ideas.append(idea)
            log.info(f"Gemini idea {i}: {idea['name']}")

        return ideas
    except Exception as e:
        log.error(f"Gemini generation failed: {e}")
        return []
