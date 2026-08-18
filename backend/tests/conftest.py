import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# ------------------------------------------------------------------
# Python import path
# ------------------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parents[1]
APP_DIR = BACKEND_DIR / "app"

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


# ------------------------------------------------------------------
# Test database safety
# ------------------------------------------------------------------

_TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

# If a dedicated test database is configured, make sure application
# imports use it instead of the normal development DATABASE_URL.
if _TEST_DATABASE_URL:
    os.environ["DATABASE_URL"] = _TEST_DATABASE_URL


@pytest.fixture(scope="session")
def test_database_url():
    url = os.getenv("TEST_DATABASE_URL")

    if not url:
        pytest.skip(
            "TEST_DATABASE_URL is not set; "
            "database/API integration tests skipped."
        )

    # Safety check so tests cannot easily run against the real database.
    if "test" not in url.lower():
        pytest.fail(
            "TEST_DATABASE_URL must point to a dedicated test database "
            "whose URL contains the word 'test'."
        )

    return url


@pytest.fixture(scope="session")
def test_engine(test_database_url):
    from db.models import Base

    engine = create_engine(test_database_url)

    Base.metadata.drop_all(bind=engine)

    yield engine

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def db_session(test_engine):
    from db.models import Base

    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
    )

    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def client(test_database_url, test_engine):
    from fastapi.testclient import TestClient

    from db.database import get_db_session
    from db.models import Base
    from main import app

    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
    )

    def override_get_db_session():
        session = TestingSessionLocal()

        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db_session] = (
        override_get_db_session
    )

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=test_engine)