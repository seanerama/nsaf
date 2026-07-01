"""Stage 2: dedup key normalization and annotation."""

from __future__ import annotations

from daily_brief.dedup import annotate, dedup_key, normalize_url
from daily_brief.models import BriefItem, HistoryEntry, Source, SourceType


def _item(title, url=None, item_id=""):
    return BriefItem(id=item_id, title=title, url=url,
                     source=Source(name="S", type=SourceType.WEB_SEARCH))


def test_url_normalization_strips_tracking_and_trailing_slash():
    a = normalize_url("https://Example.com/Post/?utm_source=x&fbclid=y")
    b = normalize_url("https://example.com/Post")
    assert a == b


def test_dedup_key_stable_across_url_variants():
    k1 = dedup_key("T", "https://example.com/a/?utm_campaign=z")
    k2 = dedup_key("Different title", "https://example.com/a")
    assert k1 == k2  # URL wins over title


def test_dedup_key_falls_back_to_title():
    assert dedup_key("Hello   World", None) == dedup_key("hello world", "")


def test_annotate_adds_prior_coverage_for_seen():
    hist = [HistoryEntry(date="2026-06-01", topic="t", title="Old", source="NYT",
                         url="https://example.com/a", dedup_key=dedup_key("Old", "https://example.com/a"))]
    items = [_item("New headline", "https://example.com/a/?utm_source=feed")]
    out = annotate(items, hist, mode="annotate")
    assert len(out) == 1
    assert out[0].id == dedup_key("New headline", "https://example.com/a")
    assert out[0].prior_coverage[0].source == "NYT"
    assert out[0].prior_coverage[0].date == "2026-06-01"


def test_annotate_drop_mode_removes_seen():
    key = dedup_key("X", "https://example.com/a")
    hist = [HistoryEntry(date="2026-06-01", topic="t", title="X", source="NYT",
                         url="https://example.com/a", dedup_key=key)]
    items = [_item("X", "https://example.com/a"), _item("Fresh", "https://example.com/b")]
    out = annotate(items, hist, mode="drop")
    assert [i.title for i in out] == ["Fresh"]


def test_annotate_assigns_id_to_new_items():
    out = annotate([_item("Brand new", "https://example.com/z")], [], mode="annotate")
    assert out[0].id == dedup_key("Brand new", "https://example.com/z")
    assert out[0].prior_coverage == []


def test_annotate_earliest_prior_coverage_wins():
    url = "https://example.com/a"
    key = dedup_key("X", url)

    def h(date, source):
        return HistoryEntry(date=date, topic="t", title="X", source=source, url=url, dedup_key=key)

    hist = [h("2026-06-10", "Late"), h("2026-06-01", "Early")]
    out = annotate([_item("X", "https://example.com/a")], hist, mode="annotate")
    assert out[0].prior_coverage[0].source == "Early"
