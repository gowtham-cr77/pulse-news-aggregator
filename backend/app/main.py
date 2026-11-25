"""FastAPI entry point for PULSE News Discovery and Aggregation Platform."""

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select

from app.api import admin, articles, auth, discovery, me
from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine, ensure_schema_migrations
from app.models.models import FeedSource
from app.seed import seed_initial_data
from app.services.ingestion_scheduler import (
    run_all_enabled_feeds,
    start_scheduler,
    stop_scheduler,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pulse.main")


def _startup_ingest_worker() -> None:
    """Fetch real-time feeds on startup for any newly added or unfetched enabled sources."""
    db = SessionLocal()
    try:
        unfetched_count = (
            db.scalar(
                select(func.count(FeedSource.id)).where(
                    FeedSource.enabled.is_(True), FeedSource.last_fetched_at.is_(None)
                )
            )
            or 0
        )
        if unfetched_count > 0:
            logger.info("Fetching %d unfetched live RSS/API sources on startup...", unfetched_count)
            summary = run_all_enabled_feeds(db, only_unfetched=True)
            logger.info(
                "Startup live ingestion complete: added=%d succeeded=%d failed=%d",
                summary.total_items_added,
                summary.feeds_succeeded,
                summary.feeds_failed,
            )
    except Exception as exc:
        logger.warning("Startup ingestion worker error: %s", exc)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Initialize schema, run lightweight migrations, seed sources, and start scheduler."""
    settings = get_settings()
    Base.metadata.create_all(bind=engine)
    ensure_schema_migrations()

    db = SessionLocal()
    try:
        seed_initial_data(db)
    finally:
        db.close()

    if settings.INGEST_ON_STARTUP:
        threading.Thread(target=_startup_ingest_worker, daemon=True).start()

    start_scheduler()
    try:
        yield
    finally:
        stop_scheduler()


settings = get_settings()

app = FastAPI(
    title="PULSE — News Discovery & Aggregation API",
    description="Free, open-source Global & Indian real-time news discovery platform with deduplication, personalization, bookmarks, and trending topics.",
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(articles.router)
app.include_router(discovery.router)
app.include_router(me.router)
app.include_router(admin.router)


@app.get("/api/health", tags=["Health"])
def health_check() -> dict:
    """Basic health endpoint."""
    return {"status": "ok", "service": settings.APP_NAME}
