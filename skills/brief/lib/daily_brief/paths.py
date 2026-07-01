"""Path helpers for the on-disk storage layout (see contracts/storage-layout.md).

All runtime data lives under a single root (``BRIEF_DATA_DIR`` or ``./data``). Timestamps
are always passed in by the caller so engine functions stay deterministic.
"""

from __future__ import annotations

import os
from pathlib import Path


def data_root() -> Path:
    """Root data directory; honors the BRIEF_DATA_DIR env var, defaults to ./data."""
    override = os.environ.get("BRIEF_DATA_DIR")
    return Path(override) if override else Path("data")


def profiles_root() -> Path:
    return data_root() / "profiles"


def profile_dir(slug: str) -> Path:
    return profiles_root() / slug


def reference_path(slug: str) -> Path:
    return profile_dir(slug) / "reference.md"


def history_path(slug: str) -> Path:
    return profile_dir(slug) / "history.md"


def kb_path(slug: str) -> Path:
    return profile_dir(slug) / "knowledge-base.md"


def briefs_root() -> Path:
    return data_root() / "briefs"


def brief_dir(slug: str, timestamp: str) -> Path:
    """Run directory for a brief. ``timestamp`` is a 'YYYY-MM-DD-HHMM' string."""
    return briefs_root() / slug / timestamp
