"""Pydantic request and response schemas for the PULSE API."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# --- Auth & Users ---

class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    display_name: str = Field(default="Reader", min_length=1, max_length=120)


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    display_name: str
    role: str
    created_at: datetime


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# --- Categories ---

class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    keywords: List[str] = Field(default_factory=list)
    article_count: int = 0


class CategoryUpdateRequest(BaseModel):
    keywords: List[str]


# --- Sources ---

class SourceSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    region: str = "global"
    source_type: str = "rss"
    enabled: bool


class AlsoSeenSource(BaseModel):
    source_id: int
    source_name: str
    url: str


# --- Articles ---

class ArticleOut(BaseModel):
    id: int
    title: str
    url: str
    normalized_url: str
    description: str
    published_at: Optional[datetime] = None
    fetched_at: datetime
    source_id: int
    source_name: str
    source_region: str = "global"
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    category_slug: Optional[str] = None
    also_seen_sources: List[AlsoSeenSource] = Field(default_factory=list)
    is_bookmarked: bool = False


class PaginatedArticlesResponse(BaseModel):
    items: List[ArticleOut]
    total: int
    page: int
    size: int
    total_pages: int


class ArticleCategoryOverrideRequest(BaseModel):
    category_id: Optional[int] = None


# --- Preferences & Bookmarks ---

class PreferencesOut(BaseModel):
    category_ids: List[int]
    categories: List[CategoryOut]


class PreferencesUpdateRequest(BaseModel):
    category_ids: List[int]


class BookmarkActionResponse(BaseModel):
    status: str
    article_id: int
    bookmarked: bool


# --- Trending ---

class TrendingTopicOut(BaseModel):
    topic: str
    mention_count: int
    time_window: str


class TrendingResponse(BaseModel):
    time_window: str
    calculated_at: datetime
    disclaimer: str = "Frequency-based indicator over recent article titles and snippets, not a claim of objective importance."
    topics: List[TrendingTopicOut]


# --- Admin Feeds & Ingestion ---

class FeedSourceCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    feed_url: str = Field(..., min_length=8, max_length=1024)
    region: str = Field(default="global", pattern="^(global|india)$")
    source_type: str = Field(default="rss", pattern="^(rss|gnews_api|newsdata_api)$")
    default_category_id: Optional[int] = None
    enabled: bool = True


class FeedSourceUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    feed_url: Optional[str] = Field(default=None, min_length=8, max_length=1024)
    region: Optional[str] = Field(default=None, pattern="^(global|india)$")
    source_type: Optional[str] = Field(default=None, pattern="^(rss|gnews_api|newsdata_api)$")
    default_category_id: Optional[int] = None
    enabled: Optional[bool] = None


class FeedSourceOut(BaseModel):
    id: int
    name: str
    feed_url: str
    region: str = "global"
    source_type: str = "rss"
    default_category_id: Optional[int] = None
    default_category_name: Optional[str] = None
    enabled: bool
    last_fetched_at: Optional[datetime] = None
    last_status: Optional[str] = None
    last_error: Optional[str] = None
    article_count: int = 0
    created_at: datetime


class IngestionRunOut(BaseModel):
    id: int
    feed_source_id: int
    feed_source_name: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    status: str
    items_found: int
    items_added: int
    duplicates_skipped: int
    error_message: Optional[str] = None


class IngestionSummaryOut(BaseModel):
    feeds_processed: int
    feeds_succeeded: int
    feeds_failed: int
    total_items_found: int
    total_items_added: int
    total_duplicates_skipped: int
    runs: List[IngestionRunOut]
