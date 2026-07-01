"""Dedup key normalization and prior-coverage annotation (see contracts/data-models.md)."""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .models import BriefItem, HistoryEntry, PriorCoverage

# Query params that never identify content — dropped during URL normalization.
_TRACKING_PREFIXES = ("utm_",)
_TRACKING_KEYS = {
    "fbclid", "gclid", "gclsrc", "dclid", "msclkid", "mc_cid", "mc_eid",
    "ref", "ref_src", "ref_url", "source", "cmpid", "igshid", "spm",
}
_WS_RE = re.compile(r"\s+")


def _is_tracking(key: str) -> bool:
    k = key.lower()
    return k in _TRACKING_KEYS or any(k.startswith(p) for p in _TRACKING_PREFIXES)


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower() or "https"
    netloc = parts.netloc.lower()
    path = parts.path.rstrip("/")
    query = urlencode(
        sorted((k, v) for k, v in parse_qsl(parts.query, keep_blank_values=False)
               if not _is_tracking(k))
    )
    # Fragments never identify distinct content for our purposes.
    return urlunsplit((scheme, netloc, path, query, ""))


def normalize_title(title: str) -> str:
    return _WS_RE.sub(" ", title.strip().lower())


def dedup_key(title: str, url: str | None) -> str:
    """Stable identity for an item: normalized URL if present, else normalized title."""
    if url and url.strip():
        return "url:" + normalize_url(url)
    return "title:" + normalize_title(title)


def annotate(
    items: list[BriefItem],
    history: list[HistoryEntry],
    mode: str = "annotate",
) -> list[BriefItem]:
    """Assign ids and prior-coverage. mode='annotate' keeps seen items; 'drop' removes them."""
    seen: dict[str, HistoryEntry] = {}
    for h in history:
        # Earliest coverage wins for the "also covered by X on DATE" note.
        if h.dedup_key not in seen or h.date < seen[h.dedup_key].date:
            seen[h.dedup_key] = h

    out: list[BriefItem] = []
    for item in items:
        key = item.id or dedup_key(item.title, item.url)
        item = item.model_copy(update={"id": key})
        prior = seen.get(key)
        if prior is not None:
            if mode == "drop":
                continue
            note = PriorCoverage(source=prior.source, date=prior.date)
            if note not in item.prior_coverage:
                item.prior_coverage = [*item.prior_coverage, note]
        out.append(item)
    return out
