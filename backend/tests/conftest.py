"""Pytest fixtures for isolated backend API and service testing."""

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure backend/ is importable
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ["INGEST_ON_STARTUP"] = "false"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-pytest-only-32-chars"

from app.core.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed_initial_data  # noqa: E402


@pytest.fixture()
def db_session(tmp_path):
    """Create a fresh SQLite database per test."""
    db_file = tmp_path / "test_pulse.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    seed_initial_data(session)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session):
    """Return a FastAPI TestClient wired to the isolated test DB session."""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
