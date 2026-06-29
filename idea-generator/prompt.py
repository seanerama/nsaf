"""Shared prompt construction for all providers."""

import json

# Temperature tiers per provider: (temp, count, label)
# OpenAI: supports 0-2.0
# Gemini: supports 0-2.0
# Anthropic: supports 0-1.0
TEMPERATURE_TIERS = {
    "openai": [
        (0.3, 3, "conservative"),
        (0.7, 3, "balanced"),
        (1.0, 2, "creative"),
        (1.4, 2, "experimental"),
    ],
    "gemini": [
        (0.3, 3, "conservative"),
        (0.7, 3, "balanced"),
        (1.0, 2, "creative"),
        (1.4, 2, "experimental"),
    ],
    "anthropic": [
        (0.2, 3, "conservative"),
        (0.5, 3, "balanced"),
        (0.8, 2, "creative"),
        (1.0, 2, "experimental"),
    ],
}
DEFAULT_TIERS = TEMPERATURE_TIERS["openai"]


def scale_tiers(tiers, total_count):
    """Proportionally rescale a tier list so its counts sum to roughly total_count.

    Each tier keeps at least 1 idea so all temperature ranges remain represented.
    """
    base = sum(c for _, c, _ in tiers)
    if base == 0 or total_count <= 0 or base == total_count:
        return list(tiers)
    factor = total_count / base
    scaled = [(t, max(1, round(c * factor)), label) for t, c, label in tiers]
    return scaled


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


def _format_list(items):
    return "\n".join(f"- {item}" for item in items) if items else "(none)"


def build_story_prompt(preferences, history_names, count, already_generated=None):
    """Build prompt requesting children's story seed ideas."""
    themes = _format_list(preferences.get("themes", []))
    settings = _format_list(preferences.get("settings", []))
    characters = _format_list(preferences.get("character_types", []))
    exclusions = _format_list(preferences.get("exclusions", []))
    art_styles = ", ".join(preferences.get("art_style_defaults", [])) or "watercolor storybook"
    tone = ", ".join(preferences.get("tone", [])) or "warm, gentle"
    target_age = preferences.get("target_age", {"min": 4, "max": 8})
    length = preferences.get("length", {"min_minutes": 4, "max_minutes": 10})

    history_section = ""
    if history_names:
        history_section = (
            "\n\nDo NOT suggest stories similar to these previously generated ideas:\n"
            + "\n".join(f"- {name}" for name in history_names[-100:])
        )

    already_section = ""
    if already_generated:
        already_section = (
            "\n\nDo NOT suggest stories similar to these (already generated this session):\n"
            + "\n".join(f"- {name}" for name in already_generated)
        )

    return f"""Generate exactly {count} unique illustrated children's audio story ideas. Each story idea must be distinctly different — different protagonists, different conflicts, different emotional arcs.

Themes to draw from:
{themes}

Settings to draw from:
{settings}

Character types to draw from:
{characters}

NEVER include any of the following:
{exclusions}

Target age range: {target_age.get('min', 4)}-{target_age.get('max', 8)} years
Target narrated length: {length.get('min_minutes', 4)}-{length.get('max_minutes', 10)} minutes
Tone: {tone}
Default art style: {art_styles}

Each story should have a clear emotional arc that resolves with comfort or quiet hope. Avoid scary imagery, on-page violence, and preachy dialogue. The story should be self-contained and tell-able as a single bedtime listen.

Respond with a JSON array of exactly {count} objects (no markdown, no code fences, no extra text):
[
  {{
    "name": "Short Story Title (4-8 words)",
    "description": "2-3 sentence story seed describing the protagonist, the conflict, and the resolution arc. Concrete and visual.",
    "target_age": "e.g. 5-8",
    "length_minutes": 6,
    "art_style_hint": "e.g. watercolor storybook",
    "themes": ["one", "or two", "themes from the list above"]
  }}
]{history_section}{already_section}"""


def build_study_prompt(preferences, history_names, count, already_generated=None):
    """Build prompt requesting study plan / textbook topic ideas."""
    domains = _format_list(preferences.get("subject_domains", []))
    source_pref = _format_list(preferences.get("source_material_tendency", []))
    exclusions = _format_list(preferences.get("exclusions", []))
    tone = ", ".join(preferences.get("tone", [])) or "technical, precise"
    levels = preferences.get("levels", {"min": "intermediate", "max": "advanced"})
    chapters = preferences.get("chapter_range", {"min": 8, "max": 20})

    history_section = ""
    if history_names:
        history_section = (
            "\n\nDo NOT suggest topics similar to these previously generated ideas:\n"
            + "\n".join(f"- {name}" for name in history_names[-100:])
        )

    already_section = ""
    if already_generated:
        already_section = (
            "\n\nDo NOT suggest topics similar to these (already generated this session):\n"
            + "\n".join(f"- {name}" for name in already_generated)
        )

    return f"""Generate exactly {count} unique study plan / textbook topic ideas. Each topic must cover a genuinely different subject area or angle — not minor variations of one another.

Subject domains to draw from:
{domains}

Source material tendency:
{source_pref}

NEVER suggest topics matching:
{exclusions}

Level range: {levels.get('min', 'intermediate')} to {levels.get('max', 'advanced')}
Chapter range: {chapters.get('min', 8)}-{chapters.get('max', 20)} chapters per topic
Tone: {tone}

Each topic should support a {chapters.get('min', 8)}+ chapter textbook with substantive technical depth. Prefer topics where an authoritative source document (RFC, vendor exam blueprint, official documentation) exists and can be linked. If no canonical source exists, set suggested_source_url to null.

Respond with a JSON array of exactly {count} objects (no markdown, no code fences, no extra text):
[
  {{
    "name": "Concise Topic Name (e.g. 'Kubernetes Networking Deep Dive')",
    "description": "2-3 sentences describing scope, the working engineer this is for, and why it is worth studying now.",
    "level": "beginner|intermediate|advanced",
    "chapters": 12,
    "suggested_source_url": "https://... (or null if none)"
  }}
]{history_section}{already_section}"""


def build_techguide_prompt(preferences, history_names, count, already_generated=None):
    """Build prompt requesting technical-guide topic ideas (interactive / comparison / explainer)."""
    domains = _format_list(preferences.get("subject_domains", []))
    source_pref = _format_list(preferences.get("source_material_tendency", []))
    length_hints = _format_list(preferences.get("length_hints", []))
    exclusions = _format_list(preferences.get("exclusions", []))
    tone = ", ".join(preferences.get("tone", [])) or "technical, precise"
    levels = preferences.get("levels", {"min": "intro", "max": "advanced"})

    history_section = ""
    if history_names:
        history_section = (
            "\n\nDo NOT suggest topics similar to these previously generated ideas "
            "(includes both techguide and study-guide history — avoid overlap):\n"
            + "\n".join(f"- {name}" for name in history_names[-100:])
        )

    already_section = ""
    if already_generated:
        already_section = (
            "\n\nDo NOT suggest topics similar to these (already generated this session):\n"
            + "\n".join(f"- {name}" for name in already_generated)
        )

    return f"""Generate exactly {count} unique technical-guide topic ideas. Each must cover a different subject area or angle — not minor variations of one another.

A technical guide is a self-contained piece of web content published to seanmahoney.ai/guides. It is NOT a multi-chapter learning track or exam prep (those are 'studyws' and are out of scope here).

For each topic, choose ONE variant — pick the one that fits the topic best, do not force a mix:
- **deep** — a multi-section deep-dive HTML guide (5-12 sections)
- **comparison** — head-to-head product/technology comparison with a feature matrix (list 3-5 products)
- **explainer** — single-page deep explanation of one concept

Subject domains to draw from:
{domains}

Source material tendency:
{source_pref}

Length hints per variant:
{length_hints}

NEVER suggest topics matching:
{exclusions}

Level range: {levels.get('min', 'intro')} to {levels.get('max', 'advanced')}
Tone: {tone}

Respond with a JSON array of exactly {count} objects (no markdown, no code fences, no extra text):
[
  {{
    "name": "Concise Topic Name",
    "description": "2-3 sentences describing scope, the working engineer this is for, and why it is worth reading.",
    "variant": "deep|comparison|explainer",
    "level": "intro|intermediate|advanced",
    "suggested_source_url": "https://... (or null if none)",
    "products": ["Product A", "Product B", "Product C"]
  }}
]

Notes:
- "products" array is REQUIRED for variant=comparison (3-5 entries) and MUST be an empty array [] for the other variants.
- "suggested_source_url" should be a real authoritative document (RFC, vendor whitepaper, official docs) when one exists; otherwise null.
- Pick variants per topic; do not bias the mix.{history_section}{already_section}"""
