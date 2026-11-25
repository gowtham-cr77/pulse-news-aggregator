"""Article Processor: URL normalization, snippet cleanup, categorization, and duplicate detection."""

import hashlib
import html
import re
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
from time import struct_time
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import Article, Category, FeedSource

TRACKING_PARAMS = {
    "fbclid",
    "gclid",
    "dclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "ref_src",
    "source",
    "si",
    "cmpid",
    "guccounter",
    "guce_referrer",
    "guce_referrer_sig",
    "igshid",
    "ncid",
    "ocid",
}

METADATA_CATEGORY_SYNONYMS: Dict[str, str] = {
    "tech": "technology",
    "technology": "technology",
    "ai": "technology",
    "artificial intelligence": "technology",
    "computing": "technology",
    "software": "technology",
    "cybersecurity": "technology",
    "internet": "technology",
    "gadgets": "technology",
    "business": "business",
    "economy": "business",
    "finance": "business",
    "markets": "business",
    "money": "business",
    "investing": "business",
    "startups": "business",
    "politics": "politics",
    "government": "politics",
    "policy": "politics",
    "elections": "politics",
    "election": "politics",
    "us politics": "politics",
    "world politics": "politics",
    "science": "science",
    "space": "science",
    "environment": "science",
    "climate": "science",
    "physics": "science",
    "biology": "science",
    "astronomy": "science",
    "research": "science",
    "nature": "science",
    "sports": "sports",
    "sport": "sports",
    "football": "sports",
    "soccer": "sports",
    "basketball": "sports",
    "cricket": "sports",
    "tennis": "sports",
    "baseball": "sports",
    "athletics": "sports",
}


def normalize_url(raw_url: str) -> str:
    """Normalize a URL by stripping tracking query params, fragments, and redundant formatting."""
    if not raw_url:
        return ""
    cleaned = raw_url.strip()
    parts = urlsplit(cleaned)
    scheme = (parts.scheme or "https").lower()
    netloc = parts.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    elif netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]

    path = parts.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    filtered_params = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=False)
        if not k.lower().startswith("utm_") and k.lower() not in TRACKING_PARAMS
    ]
    filtered_params.sort(key=lambda item: item[0].lower())
    query = urlencode(filtered_params)

    return urlunsplit((scheme, netloc, path, query, ""))


def sanitize_snippet(raw_html: Optional[str], max_length: int = 380) -> str:
    """Strip HTML tags and return a clean, bounded feed snippet."""
    if not raw_html:
        return ""
    unescaped = html.unescape(raw_html)
    soup = BeautifulSoup(unescaped, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_length:
        cut = text[: max_length - 1].rsplit(" ", 1)[0]
        return (cut if cut else text[: max_length - 1]) + "…"
    return text


def normalize_title_for_similarity(title: str) -> str:
    """Normalize headline text by removing publisher suffixes and punctuation."""
    if not title:
        return ""
    # Strip trailing " - Publisher" or " | Publisher" often added in feeds
    cleaned = re.split(r"\s+[\-|–|—|\|]\s+[A-Z0-9][^|\-–—]{1,40}$", title.strip())[0]
    cleaned = cleaned.lower()
    cleaned = re.sub(r"[^a-z0-9\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def compute_content_hash(title: str, normalized_url: str) -> str:
    """Compute a deterministic SHA-256 hash for an article's normalized title and URL."""
    base = f"{normalize_title_for_similarity(title)}|{normalized_url}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def parse_entry_datetime(entry: dict) -> Optional[datetime]:
    """Extract a timezone-aware UTC datetime from an RSS/Atom entry if available."""
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        parsed = entry.get(key)
        if isinstance(parsed, struct_time):
            try:
                return datetime(*parsed[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                pass
    for key in ("published", "updated", "pubDate"):
        raw = entry.get(key)
        if isinstance(raw, str) and raw.strip():
            try:
                dt = parsedate_to_datetime(raw.strip())
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except (TypeError, ValueError):
                pass
    return None


def classify_article(
    title: str,
    description: str,
    feed_tags: Iterable[str],
    categories: List[Category],
    default_category_id: Optional[int],
) -> Optional[int]:
    """Assign a category using feed metadata first, keyword rules second, then feed default/uncategorized."""
    by_slug: Dict[str, Category] = {c.slug.lower(): c for c in categories}

    # 1. Check feed metadata tags
    for raw_tag in feed_tags:
        tag_norm = raw_tag.strip().lower()
        if not tag_norm:
            continue
        if tag_norm in by_slug and tag_norm != "uncategorized":
            return by_slug[tag_norm].id
        if tag_norm in METADATA_CATEGORY_SYNONYMS:
            mapped_slug = METADATA_CATEGORY_SYNONYMS[tag_norm]
            if mapped_slug in by_slug:
                return by_slug[mapped_slug].id

    # 2. Keyword rule fallback over title + description
    combined = f"{title} {description}".lower()
    best_cat_id: Optional[int] = None
    best_score = 0
    for cat in categories:
        if cat.slug == "uncategorized" or not cat.keywords:
            continue
        score = 0
        for kw in cat.keywords:
            kw_clean = kw.strip().lower()
            if not kw_clean:
                continue
            pattern = r"\b" + re.escape(kw_clean) + r"\b"
            if re.search(pattern, combined):
                # Title hits weigh slightly more than snippet hits
                score += 2 if re.search(pattern, title.lower()) else 1
        if score > best_score:
            best_score = score
            best_cat_id = cat.id

    uncat = by_slug.get("uncategorized")
    uncat_id = uncat.id if uncat else None

    # Strong multi-keyword match overrides feed default; single-keyword match applies when feed has no specific default
    if best_cat_id is not None and best_score >= 2:
        return best_cat_id

    if default_category_id is not None and default_category_id != uncat_id:
        return default_category_id

    if best_cat_id is not None and best_score >= 1:
        return best_cat_id

    if default_category_id is not None:
        return default_category_id

    return uncat_id


def find_duplicate_article(
    db: Session,
    normalized_url: str,
    external_id: Optional[str],
    title: str,
    source_id: int,
    similarity_threshold: float = 0.86,
) -> Optional[Article]:
    """Locate an existing duplicate article via URL, external GUID, or conservative title similarity."""
    if normalized_url:
        by_url = db.scalar(select(Article).where(Article.normalized_url == normalized_url))
        if by_url:
            return by_url

    if external_id:
        by_guid = db.scalar(
            select(Article).where(
                Article.source_id == source_id,
                Article.external_id == external_id,
            )
        )
        if by_guid:
            return by_guid

    norm_title = normalize_title_for_similarity(title)
    if len(norm_title) < 16:
        return None

    recent_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    recent_articles = db.scalars(
        select(Article)
        .where(Article.fetched_at >= recent_cutoff)
        .order_by(Article.fetched_at.desc())
        .limit(250)
    ).all()

    for candidate in recent_articles:
        cand_norm = normalize_title_for_similarity(candidate.title)
        if not cand_norm:
            continue
        if cand_norm == norm_title:
            return candidate
        ratio = SequenceMatcher(None, norm_title, cand_norm).ratio()
        if ratio >= similarity_threshold:
            return candidate

    return None


def record_source_attribution(existing: Article, source: FeedSource, article_url: str) -> bool:
    """Retain publisher attribution on a duplicate article when covered by another source."""
    if existing.source_id == source.id:
        return False
    seen_list = list(existing.also_seen_sources or [])
    if any(item.get("source_id") == source.id for item in seen_list):
        return False
    seen_list.append(
        {
            "source_id": source.id,
            "source_name": source.name,
            "url": article_url,
        }
    )
    existing.also_seen_sources = seen_list
    return True
