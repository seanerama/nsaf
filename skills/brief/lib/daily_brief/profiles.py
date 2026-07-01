"""Profile reference.md parsing and loading (see contracts/storage-layout.md)."""

from __future__ import annotations

import re

import frontmatter

from .models import Profile, Source, SourceType, Topic
from .paths import profiles_root, reference_path

# "- source: NAME (type) URL"  — URL optional
_SOURCE_RE = re.compile(
    r"^-\s*source:\s*(?P<name>.+?)\s*\((?P<type>[\w-]+)\)\s*(?P<url>\S+)?\s*$",
    re.IGNORECASE,
)
# "- web_search: true|false"
_WEBSEARCH_RE = re.compile(r"^-\s*web_search:\s*(?P<val>true|false)\s*$", re.IGNORECASE)
# "### Topic name"
_TOPIC_RE = re.compile(r"^###\s+(?P<name>.+?)\s*$")


def _parse_source(line: str) -> Source | None:
    m = _SOURCE_RE.match(line.strip())
    if not m:
        return None
    raw_type = m.group("type").strip().lower()
    try:
        stype = SourceType(raw_type)
    except ValueError:
        # Unknown type → treat as a generic website rather than dropping the source.
        stype = SourceType.WEBSITE
    url = m.group("url")
    return Source(name=m.group("name").strip(), type=stype, url=url or None)


def parse_reference(text: str) -> Profile:
    """Parse a reference.md document into a Profile."""
    post = frontmatter.loads(text)
    meta = post.metadata
    slug = str(meta.get("slug", "")).strip()
    title = str(meta.get("title", slug)).strip()
    description = str(meta.get("description", "")).strip()

    topics: list[Topic] = []
    current: Topic | None = None
    for raw in post.content.splitlines():
        line = raw.rstrip()
        tm = _TOPIC_RE.match(line)
        if tm:
            current = Topic(name=tm.group("name").strip())
            topics.append(current)
            continue
        if current is None:
            continue
        wm = _WEBSEARCH_RE.match(line.strip())
        if wm:
            current.web_search = wm.group("val").lower() == "true"
            continue
        src = _parse_source(line)
        if src:
            current.sources.append(src)
        # unknown lines are ignored

    return Profile(slug=slug, title=title, description=description, topics=topics)


def load_profile(slug: str) -> Profile:
    """Load and parse a profile's reference.md from disk."""
    path = reference_path(slug)
    if not path.exists():
        raise FileNotFoundError(f"No reference.md for profile '{slug}' at {path}")
    return parse_reference(path.read_text(encoding="utf-8"))


def list_profiles() -> list[tuple[str, str]]:
    """Return (slug, title) for every profile on disk, sorted by slug."""
    root = profiles_root()
    if not root.exists():
        return []
    out: list[tuple[str, str]] = []
    for child in root.iterdir():
        if not child.is_dir() or not (child / "reference.md").exists():
            continue
        try:
            out.append((child.name, load_profile(child.name).title))
        except Exception:
            out.append((child.name, child.name))
    return sorted(out, key=lambda t: t[0])
