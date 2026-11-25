"""Trending Service: calculates keyword and topic frequency over recent windows."""

import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.models import Article, FeedSource, TopicTrend
from app.schemas.schemas import TrendingResponse, TrendingTopicOut

STOPWORDS = {
    "about", "above", "after", "again", "against", "all", "also", "amid", "among",
    "and", "another", "any", "are", "around", "back", "because", "been", "before",
    "being", "below", "between", "both", "but", "can", "could", "daily", "data",
    "day", "days", "despite", "did", "does", "doing", "down", "during", "each",
    "even", "every", "first", "for", "from", "get", "gets", "getting", "good",
    "great", "had", "has", "have", "having", "her", "here", "hers", "high", "him",
    "his", "how", "into", "its", "just", "last", "latest", "less", "like", "made",
    "make", "makes", "many", "may", "more", "most", "much", "must", "need", "new",
    "news", "next", "not", "now", "off", "one", "only", "other", "our", "out",
    "over", "own", "part", "per", "plan", "plans", "post", "read", "report",
    "reports", "said", "same", "say", "says", "see", "set", "she", "should",
    "show", "shows", "since", "some", "still", "study", "such", "take", "takes",
    "than", "that", "the", "their", "them", "then", "there", "these", "they",
    "this", "those", "three", "through", "time", "today", "told", "too", "top",
    "two", "under", "until", "update", "updates", "use", "used", "using", "very",
    "want", "was", "way", "week", "weeks", "well", "were", "what", "when", "where",
    "which", "while", "who", "why", "will", "with", "within", "without", "work",
    "world", "would", "year", "years", "you", "your",
}

WINDOW_MAP = {
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}


def _extract_tokens(text: str) -> List[str]:
    """Extract significant candidate unigrams and capitalized multi-word phrases."""
    tokens: List[str] = []
    # Capture capitalized bigrams such as "Artificial Intelligence" or "Federal Reserve"
    bigrams = re.findall(r"\b([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,})\b", text)
    for bg in bigrams:
        parts = bg.lower().split()
        if parts[0] not in STOPWORDS and parts[1] not in STOPWORDS:
            tokens.append(bg.strip())

    # Capture significant unigrams / acronyms
    words = re.findall(r"\b[A-Za-z][A-Za-z0-9\-]{2,}\b", text)
    for w in words:
        lw = w.lower()
        if lw in STOPWORDS or lw.isdigit():
            continue
        # Preserve well-known short uppercase acronyms like AI, EV, NASA, GDP, NFL
        if w.isupper() and 2 <= len(w) <= 6:
            tokens.append(w)
        elif len(lw) >= 4:
            tokens.append(w.title() if w[0].isupper() else lw.title())
    return tokens


def calculate_trending_topics(
    db: Session,
    time_window: str = "7d",
    limit: int = 12,
    persist: bool = True,
    region: Optional[str] = None,
) -> TrendingResponse:
    """Compute trending topic frequency from recent articles (optionally filtered by region)."""
    window_key = time_window if time_window in WINDOW_MAP else "7d"
    now = datetime.now(timezone.utc)
    cutoff = now - WINDOW_MAP[window_key]

    stmt = select(Article).where(
        (Article.published_at >= cutoff)
        | ((Article.published_at.is_(None)) & (Article.fetched_at >= cutoff))
    )
    if region and region.lower() != "all":
        stmt = stmt.join(FeedSource, FeedSource.id == Article.source_id).where(
            FeedSource.region == region.lower()
        )
    articles = db.scalars(stmt).all()

    # If the strict 24h window has no articles yet, fall back gracefully within the same region
    if not articles and window_key == "24h":
        fallback_stmt = select(Article).order_by(Article.fetched_at.desc()).limit(50)
        if region and region.lower() != "all":
            fallback_stmt = (
                select(Article)
                .join(FeedSource, FeedSource.id == Article.source_id)
                .where(FeedSource.region == region.lower())
                .order_by(Article.fetched_at.desc())
                .limit(50)
            )
        articles = db.scalars(fallback_stmt).all()

    counter: Counter[str] = Counter()
    display_case: dict[str, str] = {}

    for article in articles:
        combined = f"{article.title}. {article.description}"
        seen_in_article = set()
        for tok in _extract_tokens(combined):
            norm = tok.lower()
            if norm in seen_in_article:
                continue
            seen_in_article.add(norm)
            counter[norm] += 1
            # Prefer uppercase acronyms or multi-word capitalized labels
            if norm not in display_case or tok.isupper() or " " in tok:
                display_case[norm] = tok

    # Filter out singletons when we have enough corpus data
    min_count = 2 if len(articles) >= 6 else 1
    ranked = [
        (display_case[norm], count)
        for norm, count in counter.most_common(limit * 2)
        if count >= min_count
    ][:limit]

    if persist and (not region or region.lower() == "all"):
        db.execute(delete(TopicTrend).where(TopicTrend.time_window == window_key))
        for label, count in ranked:
            db.add(
                TopicTrend(
                    topic=label,
                    time_window=window_key,
                    mention_count=count,
                    calculated_at=now,
                )
            )
        db.commit()

    return TrendingResponse(
        time_window=window_key,
        calculated_at=now,
        topics=[
            TrendingTopicOut(topic=label, mention_count=count, time_window=window_key)
            for label, count in ranked
        ],
    )
