"""Shared prompt construction for all providers."""

import json

# Single call per provider at a moderate-high temperature for variety
DEFAULT_TEMPERATURE = 0.9


def build_prompt(preferences, history_names, count=10):
    """Build prompt requesting multiple unique ideas in one call."""
    categories = ", ".join(preferences.get("categories", []))
    exclusions = ", ".join(preferences.get("exclusions", []))
    stack = preferences.get("tech_stack", {})
    stack_str = ", ".join(f"{k}: {v}" for k, v in stack.items())
    complexity = preferences.get("complexity_range", {})
    design = preferences.get("design", {})

    history_section = ""
    if history_names:
        history_section = (
            "\n\nDo NOT suggest any of these previously generated ideas:\n"
            + "\n".join(f"- {name}" for name in history_names[-100:])
        )

    return f"""Generate exactly {count} unique and diverse web application ideas. Each idea must be completely different from the others — different domains, different user problems, different functionality. Aim for a mix of practical and creative ideas.

Categories to draw from: {categories}
Categories/types to NEVER suggest: {exclusions}
Preferred tech stack: {stack_str}
Complexity range: {complexity.get('min', 'medium')} to {complexity.get('max', 'high')}
Design preference: {design.get('tone', 'modern, clean')}, mobile first: {design.get('mobile_first', True)}

Each idea should be for a multi-page web application that could realistically be built by an AI coding agent in a single session. It should have a database, a frontend, and a backend API.

Respond with a JSON array of exactly {count} objects (no markdown, no code fences, no extra text):
[
  {{
    "name": "Short App Name",
    "description": "One sentence describing what the app does and who it's for.",
    "category": "one of the preference categories",
    "complexity": "low|medium|high",
    "suggested_stack": {{
      "frontend": "framework",
      "backend": "framework",
      "database": "database",
      "css": "css approach"
    }}
  }}
]{history_section}"""
