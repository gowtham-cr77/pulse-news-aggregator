"""Bookmark Service: manage user's saved articles."""

import math

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.models import Article, Bookmark, User
from app.schemas.schemas import AlsoSeenSource, ArticleOut, PaginatedArticlesResponse


def list_user_bookmarks(
    db: Session, user: User, page: int = 1, size: int = 20
) -> PaginatedArticlesResponse:
    """Return paginated articles saved by the authenticated user."""
    total = db.scalar(
        select(func.count(Bookmark.id)).where(Bookmark.user_id == user.id)
    ) or 0
    total_pages = math.ceil(total / size) if total > 0 else 0

    bookmarks = (
        db.scalars(
            select(Bookmark)
            .options(
                joinedload(Bookmark.article).joinedload(Article.source),
                joinedload(Bookmark.article).joinedload(Article.category),
            )
            .where(Bookmark.user_id == user.id)
            .order_by(Bookmark.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        .unique()
        .all()
    )

    items = [
        ArticleOut(
            id=bm.article.id,
            title=bm.article.title,
            url=bm.article.url,
            normalized_url=bm.article.normalized_url,
            description=bm.article.description,
            published_at=bm.article.published_at,
            fetched_at=bm.article.fetched_at,
            source_id=bm.article.source_id,
            source_name=bm.article.source.name if bm.article.source else "Unknown Source",
            source_region=bm.article.source.region if bm.article.source else "global",
            category_id=bm.article.category_id,
            category_name=bm.article.category.name if bm.article.category else "Uncategorized",
            category_slug=bm.article.category.slug if bm.article.category else "uncategorized",
            also_seen_sources=[
                AlsoSeenSource(**item)
                for item in (bm.article.also_seen_sources or [])
                if isinstance(item, dict) and {"source_id", "source_name", "url"} <= item.keys()
            ],
            is_bookmarked=True,
        )
        for bm in bookmarks
        if bm.article is not None
    ]

    return PaginatedArticlesResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        total_pages=total_pages,
    )


def add_bookmark(db: Session, user: User, article_id: int) -> bool:
    """Save an article to the user's bookmarks (idempotent). Returns False if article missing."""
    article = db.get(Article, article_id)
    if not article:
        return False

    existing = db.scalar(
        select(Bookmark).where(Bookmark.user_id == user.id, Bookmark.article_id == article_id)
    )
    if not existing:
        db.add(Bookmark(user_id=user.id, article_id=article_id))
        db.commit()
    return True


def remove_bookmark(db: Session, user: User, article_id: int) -> None:
    """Remove an article from the user's bookmarks."""
    db.execute(
        delete(Bookmark).where(Bookmark.user_id == user.id, Bookmark.article_id == article_id)
    )
    db.commit()
