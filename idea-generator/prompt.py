"""Shared prompt construction for all providers."""

import json

# Temperature tiers: (temp, count, label)
TEMPERATURE_TIERS = [
    (0.3, 3, "conservative"),
    (0.7, 3, "balanced"),
    (1.0, 2, "creative"),
    (1.3, 2, "experimental"),
]


def build_prompt(preferences, history_names, count, already_generated=None):
    """Build prompt requesting ideas. Includes already-generated ideas to avoid dupes."""
    categories = ", ".join(preferences.get("categories", []))
    exclusions = ", ".join(preferences.get("exclusions", []))
    stack = preferences.get("tech_stack", {})
    stack_str = ", ".join(f"{k}: {v}" for k, v in stack.items())
    complexity = preferences.get("complexity_range", {})
    design = preferences.get("design", {})
    target = design.get("target_audience", "")

    history_section = ""
    if history_names:
        history_section = (
            "\n\nDo NOT suggest any of these previously generated ideas:\n"
            + "\n".join(f"- {name}" for name in history_names[-100:])
        )

    already_section = ""
    if already_generated:
        already_section = (
            "\n\nDo NOT suggest ideas similar to these (already generated this session):\n"
            + "\n".join(f"- {name}" for name in already_generated)
        )

    audience_line = f"\nTarget audience: {target}" if target else ""

    return f"""Generate exactly {count} unique and diverse web application ideas. Each idea must be completely different from the others — different domains, different user problems, different functionality.

Categories to draw from: {categories}
Categories/types to NEVER suggest: {exclusions}
Preferred tech stack: {stack_str}
Complexity range: {complexity.get('min', 'medium')} to {complexity.get('max', 'high')}
Design preference: {design.get('tone', 'modern, clean')}, mobile first: {design.get('mobile_first', True)}{audience_line}

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
]{history_section}{already_section}"""
