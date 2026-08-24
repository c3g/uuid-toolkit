from pathlib import Path

from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from fastapi import Depends, FastAPI, HTTPException, Request

from sqlalchemy import text
from sqlalchemy.orm import Session
from db.database import engine, get_db_session

from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse

from api.auth import router as auth_router
from api.users import router as users_router
from api.validate import router as validate_router
from api.generate import router as generate_router
from api.identifier_database import router as identifiers_router
from api.database_management import (
    router as database_management_router,
)
from api.projects import router as projects_router
from core.oidc import (
    UnenrolledUserError,
    process_callback,
    redirect_to_cilogon,
)
from db.user_repository import get_user_by_id

#Allows imports from env
import os

#Logging import
import logging

DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

cors_origins_env = os.getenv("CORS_ORIGINS")

if cors_origins_env:
    CORS_ORIGINS = [
        origin.strip()
        for origin in cors_origins_env.split(",")
        if origin.strip()
    ]
else:
    CORS_ORIGINS = DEFAULT_CORS_ORIGINS

# Whether the login gate is enforced. Defaults to required (fails safe).
# Only an explicit "false" disables it, for local `npm run dev` frontend
# iteration where CILogon's registered redirect URI does not apply anyway.
# Production must never set this to anything but "true" or leave it unset.
AUTH_REQUIRED = (
    os.getenv("AUTH_REQUIRED", "true").strip().lower() != "false"
)

SESSION_SECRET = os.getenv("SESSION_SECRET")

if not SESSION_SECRET:
    if AUTH_REQUIRED:
        raise RuntimeError("SESSION_SECRET is not set.")

    # Auth is explicitly disabled for local dev; a real secret isn't needed.
    SESSION_SECRET = "local-dev-insecure-session-secret"

# Local Podman testing is plain HTTP; production is HTTPS and must set this
# to "true" so the session cookie is only ever sent over HTTPS.
SESSION_COOKIE_SECURE = (
    os.getenv("SESSION_COOKIE_SECURE", "false").strip().lower()
    == "true"
)

FRONTEND_DIST_DIR = (
    Path(__file__).resolve().parents[2]
    / "frontend-vite"
    / "dist"
)

logger = logging.getLogger(__name__)


app = FastAPI(
    title="UUID Toolkit API",
    description="API for validating, generating, and managing UUID identifiers.",
    version="0.1.0",
)


# Allows frontend apps like React/Vite to call this backend during development.
# Later, replace these with the actual production frontend URL.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# same_site="lax" is required, not a style choice: CILogon's redirect back
# to this app is a top-level cross-site navigation, and a "strict" cookie
# would not be sent on that request, breaking Authlib's state/nonce check.
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="uuid_toolkit_session",
    same_site="lax",
    https_only=SESSION_COOKIE_SECURE,
)


@app.get("/api/health")
def health_check() -> dict:
    """
    Basic endpoint to check whether the API is running.
    """
    return {
        "status": "ok",
        "message": "UUID Toolkit API is running.",
    }
#Checking that the database is available and ready to accept connections.
@app.get("/api/ready")
def readiness_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Database readiness check failed.")
        
        raise HTTPException(
            status_code=503,
            detail="Database is unavailable.",
        )

    return {
        "status": "ready",
        "message": "UUID Toolkit API is ready.",
    }


# Register endpoint groups.
# These create:
# POST /api/validate
# POST /api/generate
# POST /api/identifiers
app.include_router(validate_router, prefix="/api")
app.include_router(generate_router, prefix="/api")
app.include_router(identifiers_router,prefix="/api")
app.include_router(database_management_router,prefix="/api")
app.include_router(projects_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")

#Generic fallback
frontend_assets_dir = FRONTEND_DIST_DIR / "assets"

if frontend_assets_dir.is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=frontend_assets_dir),
        name="frontend-assets",
    )


def _serve_index_html() -> FileResponse:
    """
    Return the built React app, or a 404 when it hasn't been built.

    Kept separate from the login gate below so a missing frontend build
    (for example, the backend-only CI job, which never runs the frontend
    build) never silently skips authentication -- only this last step is
    conditional on the build actually existing.
    """
    index_path = FRONTEND_DIST_DIR / "index.html"

    if not index_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Frontend build not found.",
        )

    return FileResponse(index_path)


async def _resolve_page_session(
    request: Request,
    session: Session,
):
    """
    Return the signed-in user for a page request, or a
    ``RedirectResponse`` to CILogon when there is no valid session.

    This is the gate-before-content check: called by every page route
    below (never by ``/api/health`` or ``/api/ready``, and never by the
    ``/assets`` static mount) before any app content is returned.
    """
    if not AUTH_REQUIRED:
        return None

    user_id = request.session.get("user_id")

    if user_id is not None:
        user = get_user_by_id(session, user_id=user_id)

        if user is not None:
            return user

        # The session pointed at a user who no longer exists, e.g. an
        # admin removed their enrollment while they were logged in.
        request.session.clear()

    return await redirect_to_cilogon(request)


@app.get("/", include_in_schema=False)
async def serve_frontend_root(
    request: Request,
    session: Session = Depends(get_db_session),
):
    # CILogon's registered redirect URI is this root path, so the OIDC
    # callback (code + state) is handled here rather than on a
    # dedicated /auth/callback route.
    if (
        request.query_params.get("code")
        and request.query_params.get("state")
    ):
        try:
            user = await process_callback(request, session)

        except UnenrolledUserError as error:
            return PlainTextResponse(
                f"'{error.email}' authenticated successfully but "
                "has not been enrolled to use this application. "
                "Contact an administrator to request access.",
                status_code=403,
            )

        request.session["user_id"] = user.id

        # Redirect to a clean "/" so the authorization code does not
        # stay visible in the address bar or get replayed on refresh.
        return RedirectResponse("/", status_code=302)

    result = await _resolve_page_session(request, session)

    if isinstance(result, RedirectResponse):
        return result

    return _serve_index_html()


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(
    full_path: str,
    request: Request,
    session: Session = Depends(get_db_session),
):
    if full_path == "api" or full_path.startswith("api/"):
        raise HTTPException(
            status_code=404,
            detail="API endpoint not found.",
        )

    result = await _resolve_page_session(request, session)

    if isinstance(result, RedirectResponse):
        return result

    return _serve_index_html()