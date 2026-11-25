"""Article Service: browsing, pagination, keyword search, filtering, and personalization."""

import math
from datetime import datetime, time, timezone
from typing import List, Optional, Set

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.models import Article, Bookmark, Category, FeedSource, User, UserPreference
from app.schemas.schemas import AlsoSeenSource, ArticleOut, PaginatedArticlesResponse


def _serialize_article(article: Article, bookmarked_ids: Set[int]) -> ArticleOut:
    """Convert an Article ORM object into an ArticleOut response schema."""
    return ArticleOut(
        id=article.id,
        title=article.title,
        url=article.url,
        normalized_url=article.normalized_url,
        description=article.description,
        published_at=article.published_at,
        fetched_at=article.fetched_at,
        source_id=article.source_id,
        source_name=article.source.name if article.source else "Unknown Source",
        source_region=article.source.region if article.source else "global",
        category_id=article.category_id,
        category_name=article.category.name if article.category else "Uncategorized",
        category_slug=article.category.slug if article.category else "uncategorized",
        also_seen_sources=[
            AlsoSeenSource(**item)
            for item in (article.also_seen_sources or [])
            if isinstance(item, dict) and {"source_id", "source_name", "url"} <= item.keys()
        ],
        is_bookmarked=article.id in bookmarked_ids,
    )


def _get_bookmarked_ids(db: Session, user: Optional[User]) -> Set[int]:
    """Fetch the set of article IDs bookmarked by the current user."""
    if not user:
        return set()
    rows = db.scalars(select(Bookmark.article_id).where(Bookmark.user_id == user.id)).all()
    return set(rows)


def list_articles(
    db: Session,
    *,
    page: int = 1,
    size: int = 20,
    category: Optional[str] = None,
    source: Optional[str] = None,
    region: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    q: Optional[str] = None,
    prioritize_preferred: bool = False,
    current_user: Optional[User] = None,
) -> PaginatedArticlesResponse:
    """Query paginated articles with search, category/source/date filtering, and preference sorting."""
    effective_date = func.coalesce(Article.published_at, Article.fetched_at)
    stmt = select(Article).options(
        joinedload(Article.source),
        joinedload(Article.category),
    )
    count_stmt = select(func.count(Article.id))

    filters = []

    if category and category.lower() != "all":
        cat_clean = category.strip().lower()
        if cat_clean.isdigit():
            filters.append(Article.category_id == int(cat_clean))
        else:
            cat_obj = db.scalar(select(Category).where(Category.slug == cat_clean))
            if cat_obj:
                filters.append(Article.category_id == cat_obj.id)
            else:
                return PaginatedArticlesResponse(
                    items=[], total=0, page=page, size=size, total_pages=0
                )

    if source and source.lower() != "all":
        src_clean = source.strip()
        if src_clean.isdigit():
            filters.append(Article.source_id == int(src_clean))
        else:
            src_ids = db.scalars(
                select(FeedSource.id).where(func.lower(FeedSource.name) == src_clean.lower())
            ).all()
            if src_ids:
                filters.append(Article.source_id.in_(src_ids))
            else:
                return PaginatedArticlesResponse(
                    items=[], total=0, page=page, size=size, total_pages=0
                )

    if region and region.lower() != "all":
        reg_clean = region.strip().lower()
        region_source_ids = db.scalars(
            select(FeedSource.id).where(FeedSource.region == reg_clean)
        ).all()
        if region_source_ids:
            filters.append(Article.source_id.in_(region_source_ids))
        else:
            return PaginatedArticlesResponse(
                items=[], total=0, page=page, size=size, total_pages=0
            )

    if date_from is not None:
        dt_from = (
            date_from.replace(tzinfo=timezone.utc)
            if date_from.tzinfo is None
            else date_from.astimezone(timezone.utc)
        )
        filters.append(effective_date >= dt_from)

    if date_to is not None:
        dt_to = (
            date_to.replace(tzinfo=timezone.utc)
            if date_to.tzinfo is None
            else date_to.astimezone(timezone.utc)
        )
        # If passed as midnight date without time component, include the entire end day
        if dt_to.time() == time(0, 0, 0):
            dt_to = dt_to.replace(hour=23, minute=59, second=59)
        filters.append(effective_date <= dt_to)

    if q and q.strip():
        term = f"%{q.strip()}%"
        filters.append(
            or_(
                Article.title.ilike(term),
                Article.description.ilike(term),
            )
        )

    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)

    total = db.scalar(count_stmt) or 0
    total_pages = math.ceil(total / size) if total > 0 else 0

    order_clauses = []
    if prioritize_preferred and current_user is not None:
        pref_cat_ids = db.scalars(
            select(UserPreference.category_id).where(UserPreference.user_id == current_user.id)
        ).all()
        if pref_cat_ids:
            pref_rank = case((Article.category_id.in_(pref_cat_ids), 0), else_=1)
            order_clauses.append(pref_rank.asc())

    order_clauses.extend([effective_date.desc(), Article.id.desc()])

    rows = (
        db.scalars(
            stmt.order_by(*order_clauses)
            .offset((page - 1) * size)
            .limit(size)
        )
        .unique()
        .all()
    )

    bookmarked_ids = _get_bookmarked_ids(db, current_user)
    items = [_serialize_article(a, bookmarked_ids) for a in rows]

    return PaginatedArticlesResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        total_pages=total_pages,
    )


def get_article_detail(
    db: Session, article_id: int, current_user: Optional[User] = None
) -> Optional[ArticleOut]:
    """Fetch a single article with source attribution and bookmark state."""
    article = db.scalar(
        select(Article)
        .options(joinedload(Article.source), joinedload(Article.category))
        .where(Article.id == article_id)
    )
    if not article:
        return None
    bookmarked_ids = _get_bookmarked_ids(db, current_user)
    return _serialize_article(article, bookmarked_ids)
