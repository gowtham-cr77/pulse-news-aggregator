"""Feed Manager Service: CRUD operations for configured RSS/Atom and JSON News API sources."""

from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.models import Article, Category, FeedSource
from app.schemas.schemas import FeedSourceCreateRequest, FeedSourceOut, FeedSourceUpdateRequest


def list_feed_sources(
    db: Session, only_enabled: bool = False, region: Optional[str] = None
) -> List[FeedSourceOut]:
    """Return configured feed sources with article counts, region, and category names."""
    stmt = (
        select(FeedSource)
        .options(joinedload(FeedSource.default_category))
        .order_by(FeedSource.region.desc(), FeedSource.name.asc())
    )
    if only_enabled:
        stmt = stmt.where(FeedSource.enabled.is_(True))
    if region and region.lower() != "all":
        stmt = stmt.where(FeedSource.region == region.lower())
    sources = db.scalars(stmt).all()

    counts = dict(
        db.execute(
            select(Article.source_id, func.count(Article.id)).group_by(Article.source_id)
        ).all()
    )

    return [
        FeedSourceOut(
            id=src.id,
            name=src.name,
            feed_url=src.feed_url,
            region=src.region,
            source_type=src.source_type,
            default_category_id=src.default_category_id,
            default_category_name=src.default_category.name if src.default_category else None,
            enabled=src.enabled,
            last_fetched_at=src.last_fetched_at,
            last_status=src.last_status,
            last_error=src.last_error,
            article_count=counts.get(src.id, 0),
            created_at=src.created_at,
        )
        for src in sources
    ]


def create_feed_source(db: Session, payload: FeedSourceCreateRequest) -> FeedSource:
    """Create and persist a new feed source."""
    if payload.default_category_id is not None:
        cat = db.get(Category, payload.default_category_id)
        if not cat:
            raise ValueError("Invalid default_category_id")

    existing = db.scalar(select(FeedSource).where(FeedSource.feed_url == payload.feed_url.strip()))
    if existing:
        raise ValueError("A feed source with this URL already exists")

    source = FeedSource(
        name=payload.name.strip(),
        feed_url=payload.feed_url.strip(),
        region=payload.region,
        source_type=payload.source_type,
        default_category_id=payload.default_category_id,
        enabled=payload.enabled,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def update_feed_source(
    db: Session, source_id: int, payload: FeedSourceUpdateRequest
) -> Optional[FeedSource]:
    """Update an existing feed source's metadata, region, category, or enabled status."""
    source = db.get(FeedSource, source_id)
    if not source:
        return None

    if payload.name is not None:
        source.name = payload.name.strip()
    if payload.feed_url is not None:
        new_url = payload.feed_url.strip()
        dup = db.scalar(
            select(FeedSource).where(FeedSource.feed_url == new_url, FeedSource.id != source_id)
        )
        if dup:
            raise ValueError("Another feed source already uses this URL")
        source.feed_url = new_url
    if payload.region is not None:
        source.region = payload.region
    if payload.source_type is not None:
        source.source_type = payload.source_type
    if payload.default_category_id is not None:
        cat = db.get(Category, payload.default_category_id)
        if not cat:
            raise ValueError("Invalid default_category_id")
        source.default_category_id = payload.default_category_id
    if payload.enabled is not None:
        source.enabled = payload.enabled

    db.commit()
    db.refresh(source)
    return source


def delete_feed_source(db: Session, source_id: int) -> bool:
    """Delete a feed source and its cascaded articles/runs."""
    source = db.get(FeedSource, source_id)
    if not source:
        return False
    db.delete(source)
    db.commit()
    return True
