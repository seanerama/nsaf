import os
import re
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def get_env(key, default=None):
    return os.environ.get(key, default)


def load_preferences(path=None):
    if path is None:
        path = os.environ.get("NSAF_PREFERENCES_PATH", "./preferences.md")
    text = Path(path).read_text()

    prefs = {
        "categories": [],
        "exclusions": [],
        "tech_stack": {},
        "complexity_range": {"min": "medium", "max": "high"},
        "design": {"tone": "modern, clean", "mobile_first": True},
        "deployment": {"render_service_type": "web_service", "region": "oregon"},
        "model_profile": "balanced",
        "daily_quota": 30,
    }

    current_section = None
    for line in text.splitlines():
        line = line.strip()
        header = re.match(r"^##\s+(.+)$", line)
        if header:
            current_section = header.group(1).lower()
            continue

        if not line or line.startswith("#"):
            continue

        item = re.match(r"^-\s+(.+)$", line)
        kv = re.match(r"^-\s+(.+?):\s+(.+)$", line)

        if current_section == "idea categories" and item:
            prefs["categories"].append(item.group(1).strip())

        elif current_section == "exclusions" and item:
            prefs["exclusions"].append(item.group(1).strip())

        elif current_section == "tech stack" and kv:
            key = kv.group(1).strip().lower().replace(" ", "_")
            prefs["tech_stack"][key] = kv.group(2).strip()

        elif current_section == "complexity range" and kv:
            key = kv.group(1).strip().lower()
            prefs["complexity_range"][key] = kv.group(2).strip().lower()

        elif current_section == "design" and kv:
            key = kv.group(1).strip().lower().replace(" ", "_")
            value = kv.group(2).strip()
            if value.lower() in ("yes", "true"):
                value = True
            elif value.lower() in ("no", "false"):
                value = False
            prefs["design"][key] = value

        elif current_section == "deployment" and kv:
            key = kv.group(1).strip().lower().replace(" ", "_")
            prefs["deployment"][key] = kv.group(2).strip()

        elif current_section == "model profile":
            prefs["model_profile"] = line.strip()

        elif current_section == "daily quota":
            try:
                prefs["daily_quota"] = int(line.strip())
            except ValueError:
                pass

    return prefs


def _read_sections(path):
    """Parse a markdown preferences file into a dict of sections.

    Each section value is either a list of bare items or a dict of key/value
    pairs, depending on whether items use the `- key: value` shape.
    """
    text = Path(path).read_text()
    sections = {}
    current_section = None
    current_kind = None  # "list" | "dict" | None (undecided)

    for line in text.splitlines():
        stripped = line.strip()
        header = re.match(r"^##\s+(.+)$", stripped)
        if header:
            current_section = header.group(1).strip().lower()
            sections[current_section] = None
            current_kind = None
            continue

        if not stripped or stripped.startswith("#"):
            continue

        if current_section is None:
            continue

        kv = re.match(r"^-\s+(.+?):\s+(.+)$", stripped)
        item = re.match(r"^-\s+(.+)$", stripped)

        if kv:
            if current_kind is None:
                sections[current_section] = {}
                current_kind = "dict"
            if current_kind == "dict":
                sections[current_section][kv.group(1).strip().lower()] = kv.group(2).strip()
                continue
            # fall through to list mode if dict was not chosen
        if item:
            if current_kind is None:
                sections[current_section] = []
                current_kind = "list"
            if current_kind == "list":
                sections[current_section].append(item.group(1).strip())
                continue

        # Plain text under the header (no leading dash) — used for single-value
        # sections like "Model Profile" / "Daily Quota".
        if current_kind is None:
            sections[current_section] = stripped
            current_kind = "scalar"
        elif current_kind == "scalar":
            sections[current_section] += " " + stripped

    return sections


def _coerce_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def load_story_preferences(path=None):
    if path is None:
        path = os.environ.get("NSAF_STORY_PREFERENCES_PATH", "./story-preferences.md")
    sections = _read_sections(path)

    target_age = sections.get("target age") or {}
    length = sections.get("length") or {}

    return {
        "themes": sections.get("themes") or [],
        "settings": sections.get("settings") or [],
        "character_types": sections.get("character types") or [],
        "exclusions": sections.get("exclusions") or [],
        "target_age": {
            "min": _coerce_int(target_age.get("min"), 4),
            "max": _coerce_int(target_age.get("max"), 8),
        },
        "length": {
            "min_minutes": _coerce_int(length.get("min minutes"), 4),
            "max_minutes": _coerce_int(length.get("max minutes"), 10),
        },
        "art_style_defaults": sections.get("art style defaults") or [],
        "tone": sections.get("tone") or [],
        "model_profile": sections.get("model profile") or "balanced",
        "daily_quota": _coerce_int(sections.get("daily quota"), 20),
    }


def load_study_preferences(path=None):
    if path is None:
        path = os.environ.get("NSAF_STUDY_PREFERENCES_PATH", "./study-preferences.md")
    sections = _read_sections(path)

    levels = sections.get("levels") or {}
    chapter_range = sections.get("chapter range") or {}

    return {
        "subject_domains": sections.get("subject domains") or [],
        "levels": {
            "min": (levels.get("min") or "intermediate"),
            "max": (levels.get("max") or "advanced"),
        },
        "source_material_tendency": sections.get("source material tendency") or [],
        "chapter_range": {
            "min": _coerce_int(chapter_range.get("min"), 8),
            "max": _coerce_int(chapter_range.get("max"), 20),
        },
        "exclusions": sections.get("exclusions") or [],
        "tone": sections.get("tone") or [],
        "model_profile": sections.get("model profile") or "balanced",
        "daily_quota": _coerce_int(sections.get("daily quota"), 20),
    }
