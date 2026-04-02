import tempfile
from pathlib import Path
import pytest

from shared.config import load_preferences


@pytest.fixture
def prefs_file(tmp_path):
    content = """# NSAF Preferences

## Idea Categories
- sports
- fitness
- education

## Exclusions
- gambling

## Tech Stack
- Frontend: React
- Backend: Node.js
- Database: PostgreSQL
- CSS: Tailwind

## Complexity Range
- Minimum: medium
- Maximum: high

## Design
- Tone: modern, clean
- Mobile First: yes

## Deployment
- Render Service Type: web_service
- Region: oregon

## Model Profile
balanced

## Daily Quota
30
"""
    path = tmp_path / "preferences.md"
    path.write_text(content)
    return str(path)


def test_load_categories(prefs_file):
    prefs = load_preferences(prefs_file)
    assert prefs["categories"] == ["sports", "fitness", "education"]


def test_load_exclusions(prefs_file):
    prefs = load_preferences(prefs_file)
    assert prefs["exclusions"] == ["gambling"]


def test_load_tech_stack(prefs_file):
    prefs = load_preferences(prefs_file)
    assert prefs["tech_stack"]["frontend"] == "React"
    assert prefs["tech_stack"]["backend"] == "Node.js"
    assert prefs["tech_stack"]["database"] == "PostgreSQL"
    assert prefs["tech_stack"]["css"] == "Tailwind"


def test_load_complexity(prefs_file):
    prefs = load_preferences(prefs_file)
    assert prefs["complexity_range"]["min"] == "medium"
    assert prefs["complexity_range"]["max"] == "high"


def test_load_design(prefs_file):
    prefs = load_preferences(prefs_file)
    assert prefs["design"]["tone"] == "modern, clean"
    assert prefs["design"]["mobile_first"] is True


def test_load_deployment(prefs_file):
    prefs = load_preferences(prefs_file)
    assert prefs["deployment"]["render_service_type"] == "web_service"
    assert prefs["deployment"]["region"] == "oregon"


def test_load_model_profile(prefs_file):
    prefs = load_preferences(prefs_file)
    assert prefs["model_profile"] == "balanced"


def test_load_daily_quota(prefs_file):
    prefs = load_preferences(prefs_file)
    assert prefs["daily_quota"] == 30


def test_defaults_for_missing_sections(tmp_path):
    path = tmp_path / "empty.md"
    path.write_text("# NSAF Preferences\n")
    prefs = load_preferences(str(path))
    assert prefs["categories"] == []
    assert prefs["daily_quota"] == 30
    assert prefs["model_profile"] == "balanced"
