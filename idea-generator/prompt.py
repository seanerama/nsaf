"""Shared prompt construction for all providers."""

import json

TEMPERATURES = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2]


def build_prompt(preferences, history_names, rank):
    """Build the idea generation prompt for a given rank (1-10)."""
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
            + "\n".join(f"- {name}" for name in history_names)
        )

    creativity = "practical and grounded"
    if rank >= 7:
        creativity = "creative and experimental"
    elif rank >= 4:
        creativity = "moderately creative"

    return f"""Generate exactly 1 web application idea. Be {creativity}.

Categories to draw from: {categories}
Categories/types to NEVER suggest: {exclusions}
Preferred tech stack: {stack_str}
Complexity range: {complexity.get('min', 'medium')} to {complexity.get('max', 'high')}
Design preference: {design.get('tone', 'modern, clean')}, mobile first: {design.get('mobile_first', True)}

The idea should be for a multi-page web application that could realistically be built by an AI coding agent in a single session. It should have a database, a frontend, and a backend API.

Respond in this exact JSON format (no markdown, no code fences):
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
}}{history_section}"""


def get_temperature(rank):
    """Get temperature for a given rank (1-10). Rank 1 = conservative, 10 = experimental."""
    if 1 <= rank <= 10:
        return TEMPERATURES[rank - 1]
    return 0.7
