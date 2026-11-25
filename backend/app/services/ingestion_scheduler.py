"""Ingestion Scheduler: fetches RSS/Atom feeds and JSON News APIs with fault isolation."""

import logging
import threading
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional

import feedparser
import httpx
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.models import Article, Category, FeedSource, IngestionRun
from app.schemas.schemas import IngestionRunOut, IngestionSummaryOut
from app.services.article_processor import (
    classify_article,
    compute_content_hash,
    find_duplicate_article,
    normalize_url,
    parse_entry_datetime,
    record_source_attribution,
    sanitize_snippet,
)
from app.services.trending_service import calculate_trending_topics

logger = logging.getLogger("pulse.ingestion")

_scheduler: Optional[BackgroundScheduler] = None
_refresh_lock = threading.Lock()
_last_public_refresh_at: Optional[datetime] = None

MAX_ENTRIES_PER_FEED = 50


def _parse_iso_or_rfc_datetime(raw: Optional[str]) -> Optional[datetime]:
    """Parse ISO-8601 or RFC-2822 timestamp strings from JSON news APIs."""
    if not raw or not isinstance(raw, str):
        return None
    cleaned = raw.strip()
    try:
        iso_str = cleaned.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        pass
    try:
        dt = parsedate_to_datetime(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _normalize_json_api_items(
    source_type: str, payload: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Map GNews or NewsData.io JSON responses into unified feed entry dictionaries."""
    normalized: List[Dict[str, Any]] = []
    if source_type == "gnews_api":
        for item in payload.get("articles", []) or []:
            normalized.append(
                {
                    "title": item.get("title") or "",
                    "link": item.get("url") or "",
                    "id": item.get("url") or "",
                    "summary": item.get("description") or item.get("content") or "",
                    "published_dt": _parse_iso_or_rfc_datetime(item.get("publishedAt")),
                    "tags": [],
                }
            )
    elif source_type == "newsdata_api":
        for item in payload.get("results", []) or []:
            cats = item.get("category") or []
            if isinstance(cats, str):
                cats = [cats]
            normalized.append(
                {
                    "title": item.get("title") or "",
                    "link": item.get("link") or "",
                    "id": item.get("article_id") or item.get("link") or "",
                    "summary": item.get("description") or "",
                    "published_dt": _parse_iso_or_rfc_datetime(item.get("pubDate")),
                    "tags": [{"term": c} for c in cats if isinstance(c, str)],
                }
            )
    return normalized


def ingest_single_source(
    db: Session,
    source: FeedSource,
    timeout_seconds: Optional[int] = None,
    raw_feed_content: Optional[str] = None,
) -> IngestionRunOut:
    """Fetch, parse, deduplicate, and store items for one feed/API source with error isolation."""
    settings = get_settings()
    timeout = timeout_seconds or settings.FEED_FETCH_TIMEOUT_SECONDS
    started_at = datetime.now(timezone.utc)

    run = IngestionRun(
        feed_source_id=source.id,
        started_at=started_at,
        status="running",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    categories = db.scalars(select(Category)).all()
    items_found = 0
    items_added = 0
    duplicates_skipped = 0

    try:
        entries: List[Dict[str, Any]] = []
        headers = {
            "User-Agent": "PULSE-RSS-Aggregator/1.0 (+https://github.com/pulse-news-aggregator)"
        }

        if source.source_type in ("gnews_api", "newsdata_api") and raw_feed_content is None:
            params: Dict[str, str] = {}
            if source.source_type == "gnews_api":
                if not settings.GNEWS_API_KEY.strip():
                    raise ValueError("GNEWS_API_KEY is not configured")
                params["apikey"] = settings.GNEWS_API_KEY.strip()
            elif source.source_type == "newsdata_api":
                if not settings.NEWSDATA_API_KEY.strip():
                    raise ValueError("NEWSDATA_API_KEY is not configured")
                params["apikey"] = settings.NEWSDATA_API_KEY.strip()

            with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
                response = client.get(source.feed_url, params=params)
                response.raise_for_status()
                entries = _normalize_json_api_items(source.source_type, response.json())
        else:
            if raw_feed_content is None:
                with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
                    response = client.get(source.feed_url)
                    response.raise_for_status()
                    content = response.text
            else:
                content = raw_feed_content

            parsed = feedparser.parse(content)
            entries = parsed.get("entries", []) or []

            if parsed.get("bozo") and not entries:
                exc = parsed.get("bozo_exception")
                raise ValueError(f"Malformed feed: {exc}")

        entries = entries[:MAX_ENTRIES_PER_FEED]
        items_found = len(entries)

        for entry in entries:
            raw_url = (entry.get("link") or "").strip()
            raw_title = (entry.get("title") or "").strip()
            if not raw_url or not raw_title:
                continue

            norm_url = normalize_url(raw_url)
            if not norm_url:
                continue

            ext_id = (entry.get("id") or entry.get("guid") or "").strip() or None
            raw_summary = (
                entry.get("summary")
                or entry.get("description")
                or (entry.get("content")[0].get("value") if entry.get("content") else "")
            )
            snippet = sanitize_snippet(raw_summary)
            published_at = entry.get("published_dt") or parse_entry_datetime(entry)

            existing = find_duplicate_article(
                db=db,
                normalized_url=norm_url,
                external_id=ext_id,
                title=raw_title,
                source_id=source.id,
            )
            if existing is not None:
                duplicates_skipped += 1
                if record_source_attribution(existing, source, raw_url):
                    db.add(existing)
                    db.flush()
                continue

            feed_tags = [
                t.get("term", "") for t in (entry.get("tags") or []) if isinstance(t, dict)
            ]
            category_id = classify_article(
                title=raw_title,
                description=snippet,
                feed_tags=feed_tags,
                categories=categories,
                default_category_id=source.default_category_id,
            )

            article = Article(
                title=raw_title[:500],
                url=raw_url[:2048],
                normalized_url=norm_url[:2048],
                external_id=ext_id[:512] if ext_id else None,
                description=snippet,
                published_at=published_at,
                fetched_at=datetime.now(timezone.utc),
                source_id=source.id,
                category_id=category_id,
                content_hash=compute_content_hash(raw_title, norm_url),
                also_seen_sources=[],
            )
            db.add(article)
            db.flush()
            items_added += 1

        finished_at = datetime.now(timezone.utc)
        run.status = "success"
        run.finished_at = finished_at
        run.items_found = items_found
        run.items_added = items_added
        run.duplicates_skipped = duplicates_skipped
        run.error_message = None

        source.last_fetched_at = finished_at
        source.last_status = "success"
        source.last_error = None
        db.commit()
    except Exception as exc:
        db.rollback()
        finished_at = datetime.now(timezone.utc)
        err_msg = str(exc)[:1000]
        logger.warning("Feed ingestion failed for %s (%s): %s", source.name, source.feed_url, err_msg)

        run_obj = db.get(IngestionRun, run.id)
        src_obj = db.get(FeedSource, source.id)
        if run_obj:
            run_obj.status = "error"
            run_obj.finished_at = finished_at
            run_obj.items_found = items_found
            run_obj.items_added = items_added
            run_obj.duplicates_skipped = duplicates_skipped
            run_obj.error_message = err_msg
        if src_obj:
            src_obj.last_fetched_at = finished_at
            src_obj.last_status = "error"
            src_obj.last_error = err_msg
        db.commit()
        run = run_obj or run

    return IngestionRunOut(
        id=run.id,
        feed_source_id=source.id,
        feed_source_name=source.name,
        started_at=run.started_at,
        finished_at=run.finished_at,
        status=run.status,
        items_found=run.items_found,
        items_added=run.items_added,
        duplicates_skipped=run.duplicates_skipped,
        error_message=run.error_message,
    )


def run_all_enabled_feeds(
    db: Session, region: Optional[str] = None, only_unfetched: bool = False
) -> IngestionSummaryOut:
    """Iterate through enabled feed sources (optionally filtered by region) with fault isolation."""
    stmt = select(FeedSource).where(FeedSource.enabled.is_(True)).order_by(FeedSource.id.asc())
    if region and region.lower() != "all":
        stmt = stmt.where(FeedSource.region == region.lower())
    if only_unfetched:
        stmt = stmt.where(FeedSource.last_fetched_at.is_(None))
    sources = db.scalars(stmt).all()

    runs: List[IngestionRunOut] = []
    succeeded = 0
    failed = 0
    total_found = 0
    total_added = 0
    total_dups = 0

    for src in sources:
        result = ingest_single_source(db, src)
        runs.append(result)
        total_found += result.items_found
        total_added += result.items_added
        total_dups += result.duplicates_skipped
        if result.status == "success":
            succeeded += 1
        else:
            failed += 1

    try:
        calculate_trending_topics(db, time_window="24h", persist=True)
        calculate_trending_topics(db, time_window="7d", persist=True)
    except Exception as exc:
        logger.warning("Trending calculation error after ingestion: %s", exc)

    return IngestionSummaryOut(
        feeds_processed=len(runs),
        feeds_succeeded=succeeded,
        feeds_failed=failed,
        total_items_found=total_found,
        total_items_added=total_added,
        total_duplicates_skipped=total_dups,
        runs=runs,
    )


def refresh_live_feeds_with_cooldown(
    db: Session, region: Optional[str] = None, cooldown_seconds: int = 30
) -> Dict[str, Any]:
    """Allow on-demand real-time refresh from the UI with a short cooldown guard."""
    global _last_public_refresh_at
    now = datetime.now(timezone.utc)
    with _refresh_lock:
        if (
            _last_public_refresh_at is not None
            and (now - _last_public_refresh_at).total_seconds() < cooldown_seconds
        ):
            remaining = int(cooldown_seconds - (now - _last_public_refresh_at).total_seconds())
            return {
                "status": "cooldown",
                "message": f"Feeds were just refreshed. Next live sync available in {max(1, remaining)}s.",
                "total_items_added": 0,
                "feeds_processed": 0,
            }
        summary = run_all_enabled_feeds(db, region=region)
        _last_public_refresh_at = datetime.now(timezone.utc)
        return {
            "status": "refreshed",
            "message": f"Live sync complete: +{summary.total_items_added} new articles from {summary.feeds_succeeded} sources.",
            "total_items_added": summary.total_items_added,
            "feeds_processed": summary.feeds_processed,
            "feeds_succeeded": summary.feeds_succeeded,
        }


def _scheduled_job() -> None:
    """APScheduler background callback for periodic feed synchronization."""
    db = SessionLocal()
    try:
        logger.info("Starting scheduled RSS/API ingestion job...")
        summary = run_all_enabled_feeds(db)
        logger.info(
            "Scheduled ingestion complete: processed=%d succeeded=%d failed=%d added=%d",
            summary.feeds_processed,
            summary.feeds_succeeded,
            summary.feeds_failed,
            summary.total_items_added,
        )
    except Exception as exc:
        logger.exception("Unexpected scheduler error: %s", exc)
    finally:
        db.close()


def start_scheduler() -> None:
    """Start the background APScheduler interval job if not already running."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return
    settings = get_settings()
    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        _scheduled_job,
        trigger="interval",
        minutes=max(1, settings.INGESTION_INTERVAL_MINUTES),
        id="pulse_feed_ingestion",
        replace_existing=True,
        max_instances=1,
    )
    _scheduler.start()
    logger.info(
        "Ingestion scheduler started (every %d minutes).",
        settings.INGESTION_INTERVAL_MINUTES,
    )


def stop_scheduler() -> None:
    """Shut down the background scheduler cleanly."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None
