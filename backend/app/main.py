from pathlib import Path

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from fastapi import FastAPI, HTTPException

from sqlalchemy import text
from db.database import engine

from fastapi.middleware.cors import CORSMiddleware

from api.validate import router as validate_router
from api.generate import router as generate_router
from api.identifier_database import router as identifiers_router
from api.database_management import (
    router as database_management_router,
)
from api.projects import router as projects_router

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

#Generic fallback
if FRONTEND_DIST_DIR.is_dir():
    frontend_assets_dir = FRONTEND_DIST_DIR / "assets"

    if frontend_assets_dir.is_dir():
        app.mount(
            "/assets",
            StaticFiles(directory=frontend_assets_dir),
            name="frontend-assets",
        )

    @app.get("/", include_in_schema=False)
    def serve_frontend_root():
        return FileResponse(
            FRONTEND_DIST_DIR / "index.html"
        )

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(
                status_code=404,
                detail="API endpoint not found.",
            )

        return FileResponse(
            FRONTEND_DIST_DIR / "index.html"
        )