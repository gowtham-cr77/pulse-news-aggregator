"""Authenticated user routes for category preferences and saved bookmarks."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import User
from app.schemas.schemas import (
    BookmarkActionResponse,
    PaginatedArticlesResponse,
    PreferencesOut,
    PreferencesUpdateRequest,
)
from app.services.bookmark_service import add_bookmark, list_user_bookmarks, remove_bookmark
from app.services.user_service import get_user_preferences, update_user_preferences

router = APIRouter(prefix="/api/me", tags=["Personalization & Bookmarks"])


@router.get("/preferences", response_model=PreferencesOut)
def get_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PreferencesOut:
    """Get the authenticated user's preferred categories."""
    return get_user_preferences(db, current_user)


@router.put("/preferences", response_model=PreferencesOut)
def put_preferences(
    payload: PreferencesUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PreferencesOut:
    """Update the authenticated user's preferred categories."""
    try:
        return update_user_preferences(db, current_user, payload.category_ids)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/bookmarks", response_model=PaginatedArticlesResponse)
def get_bookmarks(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedArticlesResponse:
    """List the authenticated user's bookmarked articles."""
    return list_user_bookmarks(db, current_user, page=page, size=size)


@router.post("/bookmarks/{article_id}", response_model=BookmarkActionResponse)
def bookmark_article(
    article_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BookmarkActionResponse:
    """Bookmark an article for the authenticated user."""
    found = add_bookmark(db, current_user, article_id)
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    return BookmarkActionResponse(status="bookmarked", article_id=article_id, bookmarked=True)


@router.delete("/bookmarks/{article_id}", response_model=BookmarkActionResponse)
def unbookmark_article(
    article_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BookmarkActionResponse:
    """Remove an article from the authenticated user's bookmarks."""
    remove_bookmark(db, current_user, article_id)
    return BookmarkActionResponse(status="removed", article_id=article_id, bookmarked=False)
