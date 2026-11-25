"""Article & source discovery API routes."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_optional
from app.models.models import FeedSource, User
from app.schemas.schemas import ArticleOut, PaginatedArticlesResponse, SourceSummary
from app.services.article_service import get_article_detail, list_articles
from app.services.ingestion_scheduler import refresh_live_feeds_with_cooldown

router = APIRouter(prefix="/api", tags=["Articles"])


@router.get("/articles", response_model=PaginatedArticlesResponse)
def get_articles(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    category: Optional[str] = Query(default=None),
    source: Optional[str] = Query(default=None),
    region: Optional[str] = Query(default=None, pattern="^(all|india|global)$"),
    from_date: Optional[datetime] = Query(default=None, alias="from"),
    to_date: Optional[datetime] = Query(default=None, alias="to"),
    q: Optional[str] = Query(default=None),
    prioritize_preferred: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> PaginatedArticlesResponse:
    """List paginated articles with keyword search, region/category/source/date filtering."""
    return list_articles(
        db,
        page=page,
        size=size,
        category=category,
        source=source,
        region=region,
        date_from=from_date,
        date_to=to_date,
        q=q,
        prioritize_preferred=prioritize_preferred,
        current_user=current_user,
    )


@router.post("/articles/refresh")
def refresh_articles(
    region: Optional[str] = Query(default=None, pattern="^(all|india|global)$"),
    db: Session = Depends(get_db),
) -> dict:
    """Trigger a live real-time feed refresh with cooldown protection."""
    return refresh_live_feeds_with_cooldown(db, region=region)


@router.get("/articles/{article_id}", response_model=ArticleOut)
def get_article(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> ArticleOut:
    """Get article metadata, attribution, and original publisher URL."""
    article = get_article_detail(db, article_id, current_user)
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    return article


@router.get("/sources", response_model=List[SourceSummary])
def get_sources(
    region: Optional[str] = Query(default=None, pattern="^(all|india|global)$"),
    db: Session = Depends(get_db),
) -> List[SourceSummary]:
    """List configured publishers for filter dropdowns, optionally filtered by region."""
    stmt = select(FeedSource).order_by(FeedSource.name.asc())
    if region and region.lower() != "all":
        stmt = stmt.where(FeedSource.region == region.lower())
    sources = db.scalars(stmt).all()
    return [SourceSummary.model_validate(s) for s in sources]
