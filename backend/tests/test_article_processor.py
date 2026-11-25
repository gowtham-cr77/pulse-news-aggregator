"""Unit tests for Article Processor: URL normalization, snippets, categorization, deduplication."""

from datetime import datetime, timezone

from app.models.models import Article, Category, FeedSource
from app.services.article_processor import (
    classify_article,
    find_duplicate_article,
    normalize_url,
    record_source_attribution,
    sanitize_snippet,
)


def test_normalize_url_strips_tracking_params_and_fragments():
    raw = "HTTPS://WWW.Example.com/news/story-1/?utm_source=rss&utm_medium=feed&id=42&fbclid=abc#comments"
    assert normalize_url(raw) == "https://example.com/news/story-1?id=42"


def test_sanitize_snippet_strips_html_and_truncates():
    raw_html = "<p>Breaking <strong>AI</strong> research &amp; engineering update.</p>" + (" word" * 120)
    cleaned = sanitize_snippet(raw_html, max_length=120)
    assert "<p>" not in cleaned
    assert "<strong>" not in cleaned
    assert "&amp;" not in cleaned
    assert cleaned.startswith("Breaking AI research & engineering update.")
    assert len(cleaned) <= 120
    assert cleaned.endswith("…")


def test_classify_article_metadata_then_keywords_then_default():
    cats = [
        Category(id=1, name="Technology", slug="technology", keywords=["quantum", "software"]),
        Category(id=2, name="Sports", slug="sports", keywords=["cricket", "tournament"]),
        Category(id=3, name="Uncategorized", slug="uncategorized", keywords=[]),
    ]
    # Feed tag match
    assert classify_article("Quarterly Earnings", "Revenue grows", ["Tech"], cats, 3) == 1
    # Keyword fallback match
    assert classify_article("National Cricket Tournament Opens", "Matches start today", [], cats, 3) == 2
    # Default fallback
    assert classify_article("Local Community Notice", "General announcement", [], cats, 3) == 3


def test_duplicate_detection_and_source_attribution(db_session):
    src1 = FeedSource(name="Source One", feed_url="https://one.example/rss", enabled=True)
    src2 = FeedSource(name="Source Two", feed_url="https://two.example/rss", enabled=True)
    db_session.add_all([src1, src2])
    db_session.commit()

    art = Article(
        title="Major Breakthrough in Solid State Battery Density Announced - Source One",
        url="https://one.example/battery?utm_source=rss",
        normalized_url=normalize_url("https://one.example/battery?utm_source=rss"),
        external_id="guid-101",
        description="Researchers demonstrate higher energy density.",
        published_at=datetime.now(timezone.utc),
        fetched_at=datetime.now(timezone.utc),
        source_id=src1.id,
        content_hash="hash1",
        also_seen_sources=[],
    )
    db_session.add(art)
    db_session.commit()

    # Exact normalized URL match
    dup_url = find_duplicate_article(
        db_session,
        normalized_url=normalize_url("https://www.one.example/battery/?fbclid=xyz"),
        external_id=None,
        title="Different headline",
        source_id=src2.id,
    )
    assert dup_url is not None and dup_url.id == art.id

    # Conservative title similarity match across different publisher URL
    dup_title = find_duplicate_article(
        db_session,
        normalized_url="https://two.example/solid-state-batteries",
        external_id="guid-202",
        title="Major Breakthrough in Solid State Battery Density Announced | Source Two",
        source_id=src2.id,
    )
    assert dup_title is not None and dup_title.id == art.id

    changed = record_source_attribution(dup_title, src2, "https://two.example/solid-state-batteries")
    assert changed is True
    assert len(dup_title.also_seen_sources) == 1
    assert dup_title.also_seen_sources[0]["source_name"] == "Source Two"
