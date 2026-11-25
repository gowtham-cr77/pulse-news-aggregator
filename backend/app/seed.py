"""Database seeding for categories, global + Indian real-time news sources, and demo accounts."""

from typing import Dict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.models import Category, FeedSource, User, UserPreference

DEFAULT_CATEGORIES = [
    {
        "name": "Technology",
        "slug": "technology",
        "keywords": [
            "ai", "artificial intelligence", "software", "cloud", "cybersecurity",
            "chip", "semiconductor", "apple", "google", "microsoft", "openai",
            "linux", "robotics", "startup", "technology", "algorithm", "quantum",
        ],
    },
    {
        "name": "Business",
        "slug": "business",
        "keywords": [
            "market", "stocks", "economy", "inflation", "bank", "fed", "rbi",
            "sensex", "nifty", "rupee", "revenue", "earnings", "trade", "investment",
            "merger", "ceo", "gdp", "finance", "retail", "corporate", "oil", "currency",
        ],
    },
    {
        "name": "Politics",
        "slug": "politics",
        "keywords": [
            "election", "parliament", "lok sabha", "rajya sabha", "supreme court",
            "senate", "congress", "president", "minister", "policy", "bill",
            "legislation", "diplomacy", "treaty", "vote", "campaign", "government",
            "regulation", "summit",
        ],
    },
    {
        "name": "Science",
        "slug": "science",
        "keywords": [
            "nasa", "isro", "space", "climate", "astronomy", "physics", "biology",
            "genome", "research", "scientist", "telescope", "planet", "vaccine",
            "fossil", "fusion", "ocean", "environment", "laboratory",
        ],
    },
    {
        "name": "Sports",
        "slug": "sports",
        "keywords": [
            "football", "soccer", "cricket", "ipl", "bcci", "nba", "nfl", "tennis",
            "olympics", "championship", "league", "tournament", "coach", "athlete",
            "goal", "match", "grand prix", "world cup", "playoffs",
        ],
    },
    {
        "name": "Uncategorized",
        "slug": "uncategorized",
        "keywords": [],
    },
]

# Tuple format: (name, feed_url, default_category_slug, region, source_type)
DEFAULT_FEEDS = [
    # Global Sources
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index", "technology", "global", "rss"),
    ("The Verge", "https://www.theverge.com/rss/index.xml", "technology", "global", "rss"),
    ("BBC Technology", "https://feeds.bbci.co.uk/news/technology/rss.xml", "technology", "global", "rss"),
    ("BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml", "business", "global", "rss"),
    ("CNBC Top News", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114", "business", "global", "rss"),
    ("NPR Business", "https://feeds.npr.org/1006/rss.xml", "business", "global", "rss"),
    ("BBC Politics", "https://feeds.bbci.co.uk/news/politics/rss.xml", "politics", "global", "rss"),
    ("NPR Politics", "https://feeds.npr.org/1014/rss.xml", "politics", "global", "rss"),
    ("NASA Breaking News", "https://www.nasa.gov/rss/dyn/breaking_news.rss", "science", "global", "rss"),
    ("BBC Science & Environment", "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml", "science", "global", "rss"),
    ("ScienceDaily Top Science", "https://www.sciencedaily.com/rss/top/science.xml", "science", "global", "rss"),
    ("BBC Sport", "https://feeds.bbci.co.uk/sport/rss.xml", "sports", "global", "rss"),
    ("ESPN Headlines", "https://www.espn.com/espn/rss/news", "sports", "global", "rss"),
    # Indian Real-Time News Sources
    ("The Hindu — National", "https://www.thehindu.com/news/national/feeder/default.rss", "politics", "india", "rss"),
    ("The Hindu — Business", "https://www.thehindu.com/business/feeder/default.rss", "business", "india", "rss"),
    ("Indian Express — India", "https://indianexpress.com/section/india/feed/", "politics", "india", "rss"),
    ("Indian Express — Technology", "https://indianexpress.com/section/technology/feed/", "technology", "india", "rss"),
    ("NDTV India", "https://feeds.feedburner.com/ndtvnews-india-news", "politics", "india", "rss"),
    ("Times of India — Top Stories", "https://timesofindia.indiatimes.com/rssfeedstopstories.cms", "politics", "india", "rss"),
    ("Hindustan Times — India", "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml", "politics", "india", "rss"),
    ("Economic Times", "https://economictimes.indiatimes.com/rssfeedsdefault.cms", "business", "india", "rss"),
    ("Livemint News", "https://www.livemint.com/rss/news", "business", "india", "rss"),
    ("Google News — India", "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en", "uncategorized", "india", "rss"),
    ("Google News — India Sports", "https://news.google.com/rss/headlines/section/topic/SPORTS?hl=en-IN&gl=IN&ceid=IN:en", "sports", "india", "rss"),
    ("Google News — India Science", "https://news.google.com/rss/headlines/section/topic/SCIENCE?hl=en-IN&gl=IN&ceid=IN:en", "science", "india", "rss"),
]


def seed_initial_data(db: Session) -> None:
    """Ensure baseline categories, global + Indian news sources, and optional demo users exist."""
    settings = get_settings()

    slug_to_cat: Dict[str, Category] = {}
    for cat_def in DEFAULT_CATEGORIES:
        cat = db.scalar(select(Category).where(Category.slug == cat_def["slug"]))
        if not cat:
            cat = Category(
                name=cat_def["name"],
                slug=cat_def["slug"],
                keywords=cat_def["keywords"],
            )
            db.add(cat)
            db.flush()
        slug_to_cat[cat.slug] = cat

    feeds_to_seed = list(DEFAULT_FEEDS)
    if settings.GNEWS_API_KEY.strip():
        feeds_to_seed.append(
            (
                "GNews India API",
                "https://gnews.io/api/v4/top-headlines?country=in&lang=en&max=25",
                "uncategorized",
                "india",
                "gnews_api",
            )
        )
    if settings.NEWSDATA_API_KEY.strip():
        feeds_to_seed.append(
            (
                "NewsData.io India API",
                "https://newsdata.io/api/1/latest?country=in&language=en",
                "uncategorized",
                "india",
                "newsdata_api",
            )
        )

    for name, url, cat_slug, region, source_type in feeds_to_seed:
        cat = slug_to_cat.get(cat_slug)
        existing = db.scalar(select(FeedSource).where(FeedSource.feed_url == url))
        if existing:
            existing.region = region
            existing.source_type = source_type
        else:
            db.add(
                FeedSource(
                    name=name,
                    feed_url=url,
                    region=region,
                    source_type=source_type,
                    default_category_id=cat.id if cat else None,
                    enabled=True,
                )
            )

    if settings.SEED_DEMO_DATA:
        admin_email = settings.DEMO_ADMIN_EMAIL.strip().lower()
        if not db.scalar(select(User).where(User.email == admin_email)):
            db.add(
                User(
                    email=admin_email,
                    display_name="Pulse Admin",
                    password_hash=hash_password(settings.DEMO_ADMIN_PASSWORD),
                    role="admin",
                )
            )

        reader_email = settings.DEMO_READER_EMAIL.strip().lower()
        reader = db.scalar(select(User).where(User.email == reader_email))
        if not reader:
            reader = User(
                email=reader_email,
                display_name="Demo Reader",
                password_hash=hash_password(settings.DEMO_READER_PASSWORD),
                role="reader",
            )
            db.add(reader)
            db.flush()
            for pref_slug in ("technology", "science"):
                if pref_slug in slug_to_cat:
                    db.add(UserPreference(user_id=reader.id, category_id=slug_to_cat[pref_slug].id))

    db.commit()
