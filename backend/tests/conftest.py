import os
import sys
from pathlib import Path
from types import SimpleNamespace

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

# main.py fails fast if SESSION_SECRET is unset. CI never sets a real one,
# so `from main import app` would crash at collection time without this.
os.environ.setdefault(
    "SESSION_SECRET",
    "test-session-secret-not-for-production",
)


# ------------------------------------------------------------------
# Fake identities used to override the auth dependencies in tests
# ------------------------------------------------------------------

FAKE_ADMIN_USER = SimpleNamespace(
    id=1,
    email="admin@test.example",
    name="Test Admin",
    role="admin",
)

FAKE_MEMBER_USER = SimpleNamespace(
    id=2,
    email="member@test.example",
    name="Test Member",
    role="member",
)


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

    from core.auth_dependencies import (
        require_admin,
        require_authenticated_user,
    )
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

    # Every route now requires authentication. Existing tests were written
    # before the login gate existed, so `client` defaults to an
    # authenticated admin identity to keep that behavior unchanged.
    # `anonymous_client`/`member_client` below remove or narrow this.
    app.dependency_overrides[require_authenticated_user] = (
        lambda: FAKE_ADMIN_USER
    )
    app.dependency_overrides[require_admin] = (
        lambda: FAKE_ADMIN_USER
    )

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def admin_client(client):
    """
    Alias for ``client`` for readability in auth-specific tests, since
    ``client`` already defaults to an authenticated admin identity.
    """
    yield client


@pytest.fixture()
def member_client(client):
    """
    Same client, but authenticated as a member instead of an admin.

    Only ``require_authenticated_user`` is overridden here.
    ``require_admin`` is deliberately left un-overridden so its real body
    runs: it resolves the (overridden) member identity and raises a real
    403, exercising actual authorization logic instead of stubbing the
    outcome.
    """
    from core.auth_dependencies import (
        require_admin,
        require_authenticated_user,
    )
    from main import app

    app.dependency_overrides[require_authenticated_user] = (
        lambda: FAKE_MEMBER_USER
    )
    app.dependency_overrides.pop(require_admin, None)

    yield client


@pytest.fixture()
def anonymous_client(client):
    """
    Same client, but with no authentication override at all -- the real,
    session-based ``require_authenticated_user``/``require_admin`` run,
    which reject the request since no session cookie is present.
    """
    from core.auth_dependencies import (
        require_admin,
        require_authenticated_user,
    )
    from main import app

    app.dependency_overrides.pop(require_authenticated_user, None)
    app.dependency_overrides.pop(require_admin, None)

    yield client