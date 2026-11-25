"""End-to-end API integration tests verifying SRS functional requirements."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.config import get_settings
from app.models.models import Category, FeedSource
from app.services.ingestion_scheduler import ingest_single_source

SAMPLE_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Sample Tech Wire</title>
    <item>
      <title>Artificial Intelligence Compilers Reach Production Speeds</title>
      <link>https://techwire.example/articles/ai-compilers?utm_source=rss</link>
      <guid>item-1</guid>
      <category>Technology</category>
      <pubDate>Tue, 24 Nov 2026 10:00:00 GMT</pubDate>
      <description>&lt;p&gt;Artificial Intelligence compilers accelerate neural workloads.&lt;/p&gt;</description>
    </item>
    <item>
      <title>Artificial Intelligence Compilers Reach Production Speeds</title>
      <link>https://techwire.example/articles/ai-compilers?fbclid=duplicate</link>
      <guid>item-1-dup</guid>
      <category>Technology</category>
      <pubDate>Tue, 24 Nov 2026 10:05:00 GMT</pubDate>
      <description>Duplicate entry with tracking query parameter.</description>
    </item>
    <item>
      <title>Deep Ocean Telescope Discovers New Hydrothermal Vents</title>
      <link>https://techwire.example/articles/ocean-telescope</link>
      <guid>item-2</guid>
      <category>Science</category>
      <pubDate>Tue, 24 Nov 2026 09:00:00 GMT</pubDate>
      <description>Marine scientists map unexplored ocean vents using autonomous probes.</description>
    </item>
  </channel>
</rss>
"""


def _login(client, email: str, password: str) -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


def test_seeded_categories_and_minimum_ten_feeds(client, db_session):
    cats_res = client.get("/api/categories")
    assert cats_res.status_code == 200
    slugs = {c["slug"] for c in cats_res.json()}
    assert {"technology", "business", "politics", "science", "sports"}.issubset(slugs)

    settings = get_settings()
    admin_token = _login(client, settings.DEMO_ADMIN_EMAIL, settings.DEMO_ADMIN_PASSWORD)
    feeds_res = client.get(
        "/api/admin/feeds", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert feeds_res.status_code == 200
    assert len(feeds_res.json()) >= 10


def test_ingestion_dedup_and_fault_isolation(client, db_session):
    tech_cat = db_session.scalar(select(Category).where(Category.slug == "technology"))
    good_feed = FeedSource(
        name="Tech Wire Test",
        feed_url="https://techwire.example/rss.xml",
        default_category_id=tech_cat.id,
        enabled=True,
    )
    bad_feed = FeedSource(
        name="Broken Feed",
        feed_url="http://127.0.0.1:1/unreachable.xml",
        default_category_id=tech_cat.id,
        enabled=True,
    )
    db_session.add_all([good_feed, bad_feed])
    db_session.commit()

    # Ingest valid RSS payload directly (no external network needed)
    good_run = ingest_single_source(db_session, good_feed, raw_feed_content=SAMPLE_RSS_XML)
    assert good_run.status == "success"
    assert good_run.items_found == 3
    assert good_run.items_added == 2
    assert good_run.duplicates_skipped == 1

    # Simulate malformed XML feed failure -> must log error cleanly without crashing
    bad_run = ingest_single_source(db_session, bad_feed, raw_feed_content="<not-valid-xml")
    assert bad_run.status == "error"
    assert bad_run.error_message

    # Verify articles appear via API with search, category, and source filters
    list_res = client.get("/api/articles", params={"q": "compilers"})
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["total"] == 1
    article = data["items"][0]
    assert article["source_name"] == "Tech Wire Test"
    assert article["category_slug"] == "technology"

    # Verify trending topics endpoint includes disclaimer and counts
    trend_res = client.get("/api/trending", params={"window": "30d"})
    assert trend_res.status_code == 200
    assert "frequency-based" in trend_res.json()["disclaimer"].lower()


def test_user_auth_preferences_bookmarks_and_admin_rbac(client, db_session):
    # Register a fresh reader account
    reg_res = client.post(
        "/api/auth/register",
        json={
            "email": "student@college.edu",
            "password": "Password123!",
            "display_name": "BTech Student",
        },
    )
    assert reg_res.status_code == 201
    reader_token = reg_res.json()["access_token"]
    reader_headers = {"Authorization": f"Bearer {reader_token}"}

    # Reader cannot access admin endpoints
    forbidden = client.get("/api/admin/feeds", headers=reader_headers)
    assert forbidden.status_code == 403

    # Ingest sample articles
    tech_cat = db_session.scalar(select(Category).where(Category.slug == "technology"))
    sci_cat = db_session.scalar(select(Category).where(Category.slug == "science"))
    src = db_session.scalar(select(FeedSource))
    ingest_single_source(db_session, src, raw_feed_content=SAMPLE_RSS_XML)

    # Update preferences to prioritize Science
    pref_res = client.put(
        "/api/me/preferences",
        headers=reader_headers,
        json={"category_ids": [sci_cat.id]},
    )
    assert pref_res.status_code == 200
    assert pref_res.json()["category_ids"] == [sci_cat.id]

    # Prioritized home feed places Science article first while keeping Technology accessible
    feed_res = client.get(
        "/api/articles",
        headers=reader_headers,
        params={"prioritize_preferred": "true"},
    )
    assert feed_res.status_code == 200
    items = feed_res.json()["items"]
    assert len(items) == 2
    assert items[0]["category_id"] == sci_cat.id
    assert items[1]["category_id"] == tech_cat.id

    # Bookmark and unbookmark flow
    art_id = items[0]["id"]
    bm_add = client.post(f"/api/me/bookmarks/{art_id}", headers=reader_headers)
    assert bm_add.status_code == 200
    assert bm_add.json()["bookmarked"] is True

    bm_list = client.get("/api/me/bookmarks", headers=reader_headers)
    assert bm_list.status_code == 200
    assert bm_list.json()["total"] == 1
    assert bm_list.json()["items"][0]["is_bookmarked"] is True

    bm_del = client.delete(f"/api/me/bookmarks/{art_id}", headers=reader_headers)
    assert bm_del.status_code == 200
    assert client.get("/api/me/bookmarks", headers=reader_headers).json()["total"] == 0

    # Admin can add, disable, and inspect ingestion runs
    settings = get_settings()
    admin_token = _login(client, settings.DEMO_ADMIN_EMAIL, settings.DEMO_ADMIN_PASSWORD)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    created = client.post(
        "/api/admin/feeds",
        headers=admin_headers,
        json={
            "name": "Custom Campus Feed",
            "feed_url": "https://campus.example/rss.xml",
            "default_category_id": tech_cat.id,
            "enabled": True,
        },
    )
    assert created.status_code == 201
    feed_id = created.json()["id"]

    toggled = client.patch(
        f"/api/admin/feeds/{feed_id}",
        headers=admin_headers,
        json={"enabled": False},
    )
    assert toggled.status_code == 200
    assert toggled.json()["enabled"] is False

    runs = client.get("/api/admin/ingestion-runs", headers=admin_headers)
    assert runs.status_code == 200
    assert len(runs.json()) >= 1


def test_indian_news_filter_and_json_api_normalizer(client, db_session):
    from app.services.ingestion_scheduler import _normalize_json_api_items

    # Verify Indian sources are seeded alongside global sources
    in_sources = client.get("/api/sources", params={"region": "india"})
    assert in_sources.status_code == 200
    assert len(in_sources.json()) >= 10
    assert all(s["region"] == "india" for s in in_sources.json())

    # Ingest a mock Indian RSS feed and verify region=india vs region=global filtering
    in_feed = db_session.scalar(select(FeedSource).where(FeedSource.region == "india"))
    global_feed = db_session.scalar(select(FeedSource).where(FeedSource.region == "global"))
    assert in_feed is not None and global_feed is not None

    indian_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0"><channel><title>India Wire</title>
      <item>
        <title>ISRO Announces Next Lunar Lander Mission Timeline</title>
        <link>https://indiawire.example/isro-lunar</link>
        <category>Science</category>
        <description>Indian space agency details upcoming polar landing tests.</description>
      </item>
    </channel></rss>"""
    ingest_single_source(db_session, in_feed, raw_feed_content=indian_xml)
    ingest_single_source(db_session, global_feed, raw_feed_content=SAMPLE_RSS_XML)

    india_res = client.get("/api/articles", params={"region": "india"})
    assert india_res.status_code == 200
    assert india_res.json()["total"] == 1
    assert india_res.json()["items"][0]["source_region"] == "india"

    global_res = client.get("/api/articles", params={"region": "global"})
    assert global_res.status_code == 200
    assert global_res.json()["total"] == 2
    assert all(item["source_region"] == "global" for item in global_res.json()["items"])

    # Verify JSON News API normalizers (GNews & NewsData.io)
    gnews_items = _normalize_json_api_items(
        "gnews_api",
        {"articles": [{"title": "RBI Policy Update", "url": "https://example.in/rbi", "description": "Rates held steady", "publishedAt": "2026-11-25T08:00:00Z"}]},
    )
    assert len(gnews_items) == 1 and gnews_items[0]["title"] == "RBI Policy Update"

    newsdata_items = _normalize_json_api_items(
        "newsdata_api",
        {"results": [{"title": "Sensex Climbs", "link": "https://example.in/sensex", "article_id": "nd-1", "description": "Markets rally", "pubDate": "2026-11-25 08:30:00", "category": ["business"]}]},
    )
    assert len(newsdata_items) == 1 and newsdata_items[0]["tags"][0]["term"] == "business"
