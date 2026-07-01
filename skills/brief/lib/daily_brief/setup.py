"""Profile bootstrap & scaffolding.

Stage 1 introduces the built-in General profile. Stage 4 expands this with template/sample
driven scaffolding for arbitrary profiles.
"""

from __future__ import annotations

from pathlib import Path

from .paths import history_path, kb_path, profile_dir, reference_path

_GENERAL_REFERENCE = """\
---
slug: general
title: General
description: A general-knowledge lens for un-scoped briefs. Frames why each item matters \
to a curious generalist keeping a broad eye on the world.
---

## Topics

### General news
- web_search: true
"""

_EMPTY_TOPICS = """\

## Topics

### Example topic
- web_search: true
- source: Example Site (website) https://example.com
"""

_SAMPLE_TOPICS = """\

## Topics

### Model releases
- web_search: true
- source: Anthropic News (news) https://www.anthropic.com/news
- source: Simon Willison (blog) https://simonwillison.net

### AI agents
- web_search: true
- source: Stratechery (blog) https://stratechery.com
- source: Latent Space (blog) https://www.latent.space
"""


def _reference_doc(slug: str, title: str, description: str, body: str) -> str:
    return (
        "---\n"
        f"slug: {slug}\n"
        f"title: {title}\n"
        f"description: {description}\n"
        "---\n"
        f"{body}"
    )


def general_reference() -> str:
    """The built-in General/Default profile reference.md content."""
    return _GENERAL_REFERENCE


def scaffold_profile(
    slug: str,
    title: str,
    description: str,
    from_sample: bool = False,
    *,
    force: bool = False,
) -> Path:
    """Create a new profile's reference.md (+ empty history/KB). Returns the reference path."""
    body = _SAMPLE_TOPICS if from_sample else _EMPTY_TOPICS
    text = _reference_doc(slug, title, description, body)
    return _write_profile_files(slug, text, force=force)


def _write_profile_files(slug: str, reference_text: str, *, force: bool = False) -> Path:
    pdir = profile_dir(slug)
    pdir.mkdir(parents=True, exist_ok=True)
    ref = reference_path(slug)
    if ref.exists() and not force:
        raise FileExistsError(f"Profile '{slug}' already exists at {ref}")
    ref.write_text(reference_text, encoding="utf-8")
    # Create empty history + KB if absent (never clobber existing logs).
    hp = history_path(slug)
    if not hp.exists():
        hp.write_text("", encoding="utf-8")
    kp = kb_path(slug)
    if not kp.exists():
        kp.write_text(f"# Knowledge Base — {slug}\n", encoding="utf-8")
    return ref


def ensure_general(force: bool = False) -> Path:
    """Create the General profile if missing (or overwrite when force=True)."""
    ref = reference_path("general")
    if ref.exists() and not force:
        return ref
    return _write_profile_files("general", general_reference(), force=force)
