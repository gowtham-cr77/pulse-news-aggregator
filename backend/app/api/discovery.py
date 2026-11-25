"""Category and Trending Topics API routes."""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Article, Category, FeedSource
from app.schemas.schemas import CategoryOut, TrendingResponse
from app.services.trending_service import calculate_trending_topics

router = APIRouter(prefix="/api", tags=["Discovery"])


@router.get("/categories", response_model=List[CategoryOut])
def get_categories(
    region: Optional[str] = Query(default=None, pattern="^(all|india|global)$"),
    db: Session = Depends(get_db),
) -> List[CategoryOut]:
    """List available news categories along with current article counts (optionally by region)."""
    categories = db.scalars(select(Category).order_by(Category.id.asc())).all()
    count_stmt = select(Article.category_id, func.count(Article.id)).group_by(Article.category_id)
    if region and region.lower() != "all":
        count_stmt = count_stmt.join(FeedSource, FeedSource.id == Article.source_id).where(
            FeedSource.region == region.lower()
        )
    counts = dict(db.execute(count_stmt).all())
    return [
        CategoryOut(
            id=c.id,
            name=c.name,
            slug=c.slug,
            keywords=c.keywords or [],
            article_count=counts.get(c.id, 0),
        )
        for c in categories
    ]


@router.get("/trending", response_model=TrendingResponse)
def get_trending(
    window: str = Query(default="7d", pattern="^(24h|7d|30d)$"),
    region: Optional[str] = Query(default=None, pattern="^(all|india|global)$"),
    limit: int = Query(default=10, ge=1, le=25),
    db: Session = Depends(get_db),
) -> TrendingResponse:
    """Return frequency-based trending keywords/topics over the requested recent window."""
    return calculate_trending_topics(
        db, time_window=window, limit=limit, persist=False, region=region
    )
