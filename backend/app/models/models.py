"""Relational data model for PULSE matching Section 8 of the SRS."""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


class User(Base):
    """Registered reader or administrator account."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False, default="Reader")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="reader")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    preferences: Mapped[List["UserPreference"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    bookmarks: Mapped[List["Bookmark"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Category(Base):
    """News topic category with configurable fallback keyword rules."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    keywords: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)

    feed_sources: Mapped[List["FeedSource"]] = relationship(back_populates="default_category")
    articles: Mapped[List["Article"]] = relationship(back_populates="category")


class FeedSource(Base):
    """Configured RSS/Atom publisher source."""

    __tablename__ = "feed_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    feed_url: Mapped[str] = mapped_column(String(1024), unique=True, nullable=False)
    region: Mapped[str] = mapped_column(String(20), nullable=False, default="global", index=True)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False, default="rss")
    default_category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_fetched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    default_category: Mapped[Optional["Category"]] = relationship(back_populates="feed_sources")
    articles: Mapped[List["Article"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )
    ingestion_runs: Mapped[List["IngestionRun"]] = relationship(
        back_populates="feed_source", cascade="all, delete-orphan"
    )


class Article(Base):
    """Aggregated news article metadata and snippet (never full-text republication)."""

    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    normalized_url: Mapped[str] = mapped_column(String(2048), unique=True, nullable=False, index=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("feed_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    also_seen_sources: Mapped[List[dict]] = mapped_column(JSON, nullable=False, default=list)

    source: Mapped["FeedSource"] = relationship(back_populates="articles")
    category: Mapped[Optional["Category"]] = relationship(back_populates="articles")
    bookmarks: Mapped[List["Bookmark"]] = relationship(
        back_populates="article", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_articles_pub_fetch", "published_at", "fetched_at"),
    )


class UserPreference(Base):
    """User's preferred categories for feed personalization."""

    __tablename__ = "user_preferences"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True
    )

    user: Mapped["User"] = relationship(back_populates="preferences")
    category: Mapped["Category"] = relationship()


class Bookmark(Base):
    """User's saved/bookmarked articles."""

    __tablename__ = "bookmarks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    article_id: Mapped[int] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    user: Mapped["User"] = relationship(back_populates="bookmarks")
    article: Mapped["Article"] = relationship(back_populates="bookmarks")

    __table_args__ = (
        UniqueConstraint("user_id", "article_id", name="uq_user_article_bookmark"),
    )


class IngestionRun(Base):
    """Audit log of every feed fetch attempt for admin visibility and fault isolation."""

    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    feed_source_id: Mapped[int] = mapped_column(
        ForeignKey("feed_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)  # running, success, error
    items_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_added: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicates_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    feed_source: Mapped["FeedSource"] = relationship(back_populates="ingestion_runs")


class TopicTrend(Base):
    """Derived frequency counts of trending topic keywords over a recent window."""

    __tablename__ = "topic_trends"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    time_window: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # e.g., 24h, 7d
    mention_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
