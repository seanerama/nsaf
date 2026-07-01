"""Shared test fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture()
def data_dir(tmp_path, monkeypatch):
    """Point BRIEF_DATA_DIR at a temp dir for the duration of a test."""
    monkeypatch.setenv("BRIEF_DATA_DIR", str(tmp_path))
    return tmp_path
