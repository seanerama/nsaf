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
