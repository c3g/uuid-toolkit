from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.validate import router as validate_router
from api.generate import router as generate_router
from api.identifier_database import router as identifiers_router
from api.database_management import (
    router as database_management_router,
)


app = FastAPI(
    title="UUID / CPHI Toolkit API",
    description="API for validating and generating UUID/CPHI identifiers.",
    version="0.1.0",
)


# Allows frontend apps like React/Vite to call this backend during development.
# Later, replace these with the actual production frontend URL.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
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
        "message": "UUID / CPHI Toolkit API is running.",
    }


@app.get("/api/options")
def get_options() -> dict:
    """
    Provides frontend dropdown options.

    The frontend can use this to dynamically show:
    - available modes
    - available identifier schemas
    - UUID versions
    - CPHI entity types
    - allowed CPHI variants depending on patient/sample type
    """
    return {
        "modes": ["validate", "generate"],

        "identifier_types": [
            "UUID",
            "CPHI",
        ],

        "uuid_versions": [4],

        "cphi_entity_types": [
            "patient",
            "sample",
        ],

        # Variant is optional.
        # If the user chooses no variant, the backend uses base CPHI format:
        # PROJECT-123456
        #
        # If the user chooses a variant, the backend uses modified CPHI format:
        # PROJECT-123456_VARIANT_1234
        "cphi_variants_by_entity_type": {
            "patient": [
                "SPE",
            ],
            "sample": [
                "EXP",
                "RG",
                "ANA",
                "LIB",
                "WRK",
            ],
        },

        "supported_file_extensions": [
            ".csv",
            ".json",
        ],

        "default_output_id_field": "identifier",
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