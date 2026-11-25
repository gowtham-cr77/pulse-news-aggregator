# PULSE — News Discovery & Aggregation Platform

PULSE is a free, open-source web-based news discovery and aggregation platform built with **FastAPI**, **SQLAlchemy**, **APScheduler**, and **React + Tailwind CSS**. It collects article metadata and short RSS/Atom snippets from multiple configured publishers into one searchable, deduplicated, personalized reading experience while linking directly back to the original publishers.

---

## Key Features (SRS Compliance)

- **Multi-Source Real-Time RSS/Atom & News API Ingestion (`FR-01`, `FR-02`)**: Pre-configured with **25 real-time news sources** across **Global** (13 feeds) and **Indian News** (12 feeds including The Hindu, Indian Express, NDTV India, Times of India, Hindustan Times, Economic Times, Livemint, and Google News India), plus optional support for **GNews** and **NewsData.io** JSON APIs (`GNEWS_API_KEY` / `NEWSDATA_API_KEY`). Runs automatically every 30 minutes, on startup for new sources, and on demand via **Refresh Live**.
- **Indian News & Regional Filtering**: Dedicated **Indian News** filter (`region=india`) in the navigation bar and feed toolbar that scopes articles, publisher dropdowns, category counts, and Trending Topics specifically to real-time Indian coverage.
- **Article Browsing & Pagination (`FR-03`)**: Paginated unified feed sorted by publication date (with fallback to ingestion timestamp).
- **Automated Categorization (`FR-04`)**: Uses feed metadata tags first, configurable keyword rules second, feed default category third, and an `Uncategorized` fallback—plus administrator override controls.
- **Keyword Search & Filtering (`FR-05`)**: Full search across article headlines and descriptions (`q`), plus filtering by category, publisher (`source`), and date range (`from` / `to`).
- **URL Normalization & Duplicate Detection (`FR-06`)**: Strips tracking parameters (`utm_*`, `fbclid`, `gclid`, fragments), checks external GUIDs and conservative headline similarity, and retains cross-source attribution (`also_seen_sources`) when multiple publishers cover the same story.
- **User Accounts, Personalization & Bookmarks (`FR-07`, `FR-08`, `FR-09`)**: Secure registration & login using bcrypt password hashing and JWT bearer tokens. Readers can save bookmarks and choose preferred categories for the **"For You"** prioritized feed.
- **Trending Topics (`FR-10`)**: Frequency-based keyword/phrase analysis over recent time windows (`24h`, `7d`), clearly labeled as a frequency indicator rather than editorial importance.
- **Ethical Source Attribution (`FR-11`)**: Stores only metadata and short feed-provided snippets, displays publisher badges prominently, and links directly to original publisher URLs.
- **Admin Dashboard (`FR-12`)**: Role-protected control center to add, edit, enable/disable, delete, and sync RSS/Atom feeds, inspect ingestion health & error logs, and tune category keyword rules.

---

## Architecture

```
placement-project/
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI routers (auth, articles, discovery, me, admin)
│   │   ├── core/           # Config, SQLAlchemy DB engine, JWT & bcrypt security
│   │   ├── models/         # ORM entities (User, Category, FeedSource, Article, etc.)
│   │   ├── schemas/        # Pydantic request/response contracts
│   │   ├── services/       # Modular business logic:
│   │   │   ├── feed_manager.py
│   │   │   ├── ingestion_scheduler.py
│   │   │   ├── article_processor.py
│   │   │   ├── article_service.py
│   │   │   ├── user_service.py
│   │   │   ├── bookmark_service.py
│   │   │   └── trending_service.py
│   │   ├── seed.py         # Default categories, 13 RSS feeds, demo accounts
│   │   └── main.py         # FastAPI app & APScheduler lifespan
│   ├── tests/              # Unit and API integration tests (pytest)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/client.js   # REST API client
│   │   ├── components/     # Navbar, ArticleCard, ArticleDetailModal, TrendingSidebar, AdminDashboard, AuthModal, PreferencesModal
│   │   └── App.jsx
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml      # Optional PostgreSQL + Backend + Frontend stack
├── .env.example
└── start-dev.ps1           # One-click local dev launcher (Windows PowerShell)
```

---

## Quick Start (Local Zero-Config with SQLite)

### 1. Backend Setup
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
The API and interactive Swagger docs will be available at:
- API: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`

### 2. Frontend Setup
```powershell
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

> **Tip (Windows):** You can also run `.\start-dev.ps1` from the project root to launch both servers together.

---

## Optional Docker + PostgreSQL Deployment

Copy `.env.example` to `.env` (update `JWT_SECRET_KEY` before deploying) and run:
```bash
docker compose up --build
```
This provisions PostgreSQL 16, the FastAPI backend, and the Nginx-served React frontend on `http://localhost:8080`.

---

## Demo Accounts (Seeded in Development)

| Role | Email | Password | Capabilities |
| :--- | :--- | :--- | :--- |
| **Reader** | `reader@pulse.org` | `Reader@123` | Bookmarks, preferred categories, "For You" feed |
| **Administrator** | `admin@pulse.org` | `Admin@123` | All reader features + Feed Manager, Manual Sync, Ingestion Logs, Rule Overrides |

*(Guests can browse, search, filter, and view trending topics without signing in.)*

---

## Running Automated Tests

```powershell
backend\.venv\Scripts\python -m pytest backend\tests -v
```
Tests run against an isolated temporary SQLite database and mock RSS payloads so they execute deterministically without external network dependencies.
