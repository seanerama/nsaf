"""Per-profile knowledge base writer (written in v1, queried in v2)."""

from __future__ import annotations

from .paths import kb_path


def append_kb(slug: str, learnings: list[str], date: str) -> int:
    """Append a dated section of learnings to knowledge-base.md. Returns count written."""
    learnings = [item.strip() for item in learnings if item and item.strip()]
    if not learnings:
        return 0
    path = kb_path(slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(f"# Knowledge Base — {slug}\n", encoding="utf-8")
    with path.open("a", encoding="utf-8") as fh:
        fh.write(f"\n## {date}\n\n")
        for item in learnings:
            fh.write(f"- {item}\n")
    return len(learnings)
