"""Administrator API routes for feed management, ingestion triggers, logs, and overrides."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.models import Article, Category, FeedSource, IngestionRun, User
from app.schemas.schemas import (
    ArticleCategoryOverrideRequest,
    CategoryOut,
    CategoryUpdateRequest,
    FeedSourceCreateRequest,
    FeedSourceOut,
    FeedSourceUpdateRequest,
    IngestionRunOut,
    IngestionSummaryOut,
)
from app.services.feed_manager import (
    create_feed_source,
    delete_feed_source,
    list_feed_sources,
    update_feed_source,
)
from app.services.ingestion_scheduler import ingest_single_source, run_all_enabled_feeds
from app.services.trending_service import calculate_trending_topics

router = APIRouter(prefix="/api/admin", tags=["Administration"])


def _to_feed_out(db: Session, src: FeedSource) -> FeedSourceOut:
    """Helper to return FeedSourceOut for a single FeedSource."""
    items = list_feed_sources(db)
    for item in items:
        if item.id == src.id:
            return item
    return FeedSourceOut(
        id=src.id,
        name=src.name,
        feed_url=src.feed_url,
        default_category_id=src.default_category_id,
        default_category_name=src.default_category.name if src.default_category else None,
        enabled=src.enabled,
        last_fetched_at=src.last_fetched_at,
        last_status=src.last_status,
        last_error=src.last_error,
        article_count=0,
        created_at=src.created_at,
    )


@router.get("/feeds", response_model=List[FeedSourceOut])
def admin_list_feeds(
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> List[FeedSourceOut]:
    """List all configured RSS/Atom feed sources and their latest fetch health."""
    return list_feed_sources(db)


@router.post("/feeds", response_model=FeedSourceOut, status_code=status.HTTP_201_CREATED)
def admin_create_feed(
    payload: FeedSourceCreateRequest,
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> FeedSourceOut:
    """Add a new RSS/Atom feed source."""
    try:
        src = create_feed_source(db, payload)
        return _to_feed_out(db, src)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch("/feeds/{source_id}", response_model=FeedSourceOut)
@router.put("/feeds/{source_id}", response_model=FeedSourceOut)
def admin_update_feed(
    source_id: int,
    payload: FeedSourceUpdateRequest,
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> FeedSourceOut:
    """Edit, enable, or disable a feed source."""
    try:
        src = update_feed_source(db, source_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not src:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feed source not found")
    return _to_feed_out(db, src)


@router.delete("/feeds/{source_id}")
def admin_delete_feed(
    source_id: int,
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Delete a feed source."""
    if not delete_feed_source(db, source_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feed source not found")
    return {"status": "deleted", "id": source_id}


@router.post("/feeds/ingest", response_model=IngestionSummaryOut)
def admin_ingest_all(
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> IngestionSummaryOut:
    """Manually trigger ingestion across all enabled feed sources."""
    return run_all_enabled_feeds(db)


@router.post("/feeds/{source_id}/ingest", response_model=IngestionRunOut)
def admin_ingest_one(
    source_id: int,
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> IngestionRunOut:
    """Manually trigger ingestion for a specific feed source."""
    src = db.get(FeedSource, source_id)
    if not src:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feed source not found")
    result = ingest_single_source(db, src)
    calculate_trending_topics(db, time_window="7d", persist=True)
    return result


@router.get("/ingestion-runs", response_model=List[IngestionRunOut])
def admin_ingestion_runs(
    limit: int = Query(default=40, ge=1, le=200),
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> List[IngestionRunOut]:
    """Return recent ingestion run history logs for admin inspection."""
    runs = (
        db.scalars(
            select(IngestionRun)
            .options(joinedload(IngestionRun.feed_source))
            .order_by(IngestionRun.started_at.desc())
            .limit(limit)
        )
        .unique()
        .all()
    )
    return [
        IngestionRunOut(
            id=r.id,
            feed_source_id=r.feed_source_id,
            feed_source_name=r.feed_source.name if r.feed_source else "Deleted Source",
            started_at=r.started_at,
            finished_at=r.finished_at,
            status=r.status,
            items_found=r.items_found,
            items_added=r.items_added,
            duplicates_skipped=r.duplicates_skipped,
            error_message=r.error_message,
        )
        for r in runs
    ]


@router.patch("/categories/{category_id}", response_model=CategoryOut)
def admin_update_category_keywords(
    category_id: int,
    payload: CategoryUpdateRequest,
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> CategoryOut:
    """Update configurable keyword rules for a category."""
    cat = db.get(Category, category_id)
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    cat.keywords = [kw.strip().lower() for kw in payload.keywords if kw.strip()]
    db.commit()
    db.refresh(cat)
    return CategoryOut(id=cat.id, name=cat.name, slug=cat.slug, keywords=cat.keywords or [])


@router.patch("/articles/{article_id}/category")
def admin_override_article_category(
    article_id: int,
    payload: ArticleCategoryOverrideRequest,
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Allow an administrator to override an article's assigned category."""
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    if payload.category_id is not None and not db.get(Category, payload.category_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid category_id")
    article.category_id = payload.category_id
    db.commit()
    return {"status": "updated", "article_id": article_id, "category_id": article.category_id}
