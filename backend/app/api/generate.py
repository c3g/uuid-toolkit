"""
API route for identifier generation.

This file defines the ``POST /generate`` endpoint used by the toolkit page. It
receives the uploaded file and form data, prepares the request values, runs the
generation pipeline, and then compares the generated identifiers with the
database.

The main request flow is:

    ToolkitPage.jsx
        -> POST /generate
        -> api/utils.py
        -> core/pipeline.py
        -> strategy selected by registry.py
        -> db/comparison.py
        -> response returned to the frontend

How this file connects to the project
-------------------------------------
- ``ToolkitPage.jsx`` sends the uploaded file, strategy name, config, column
  names, optional sheet name, and selected database project.
- ``api/utils.py`` cleans and validates request values before the pipeline runs.
- ``run_generation_pipeline()`` parses the file and generates identifiers using
  the selected strategy.
- ``get_hard_reserved_identifiers_for_generation()`` gives the pipeline the
  identifiers that are already reserved inside the selected database scope.
- ``compare_pipeline_result_to_database()`` performs the final hard-conflict and
  soft-warning checks.
- ``get_db_session()`` provides the SQLAlchemy session used for database checks.

Adding a new strategy
---------------------
This route normally does not need a new branch when a strategy is added because
the strategy name and config are passed into the shared utility, registry, and
pipeline layers.

For a new strategy, update:

1. The strategy class and ``registry.py``.
2. ``api/utils.py`` so the config is validated and normalized.
3. ``ConfigPanel.jsx`` with the strategy option and controls.
4. ``ToolkitPage.jsx`` so ``buildConfig()`` sends the required config values.
5. Generation and pipeline tests.

This route only needs a direct change when the new strategy requires a new form
field that cannot be included inside ``config_json``.
"""

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from sqlalchemy.orm import Session

from api.utils import (
    clean_optional_string,
    infer_file_type,
    normalize_strategy_name,
    parse_config_json,
    validate_and_normalize_config,
)
from core.auth_dependencies import require_authenticated_user
from core.pipeline import run_generation_pipeline
from db.comparison import (
    compare_pipeline_result_to_database,
    get_hard_reserved_identifiers_for_generation,
)
from db.database import get_db_session


router = APIRouter(
    dependencies=[Depends(require_authenticated_user)],
)


@router.post("/generate")
async def generate_identifiers(
    file: UploadFile = File(...),
    strategy_name: str = Form(...),
    config_json: str = Form("{}"),
    id_name: str | None = Form(None),
    output_id_field: str | None = Form(None),
    sheet_name: str | None = Form(None),
    project_id: int | None = Form(None),
    session: Session = Depends(get_db_session),
) -> dict:
    """
    Generate identifiers from an uploaded file.

    The route prepares the request, reserves identifiers already stored in the
    selected database scope, runs the generation pipeline, and performs one
    final database comparison before returning the result.

    Parameters
    ----------
    file:
        Uploaded CSV, JSON, or XLSX file.

    strategy_name:
        Selected identifier strategy, such as ``UUID``, ``CPHI``, ``PCGL``, or
        ``CUSTOM``.

    config_json:
        JSON string containing the selected strategy's configuration.

        UUID example:

            {
                "version": 4
            }

        CPHI example:

            {
                "project_code": "NRGI",
                "entity_type": "sample"
            }

        PCGL derived-generation example:

            {
                "project_code": "NRGI",
                "entity_type": "sample",
                "variants": ["EXP", "LIB"]
            }

        CUSTOM example:

            {
                "prefix_mode": "fixed",
                "fixed_prefix": "TEST",
                "connector": "-",
                "suffix_type": "numeric",
                "suffix_length": 6
            }

    id_name:
        Optional column containing existing identifiers. This is required for
        workflows that derive new identifiers from an existing base ID.

    output_id_field:
        Optional output column for normal single-column generation. It defaults
        to ``"identifier"`` when no value is provided.

    sheet_name:
        Optional worksheet name for XLSX uploads. The parser uses the active
        worksheet when no name is provided.

    project_id:
        Optional database project used to decide which stored identifiers are
        hard conflicts. Matches outside the selected project may be returned as
        soft warnings.

    session:
        Database session provided by ``get_db_session()``.

    Returns
    -------
    dict
        Final generation result after the pipeline and database comparison.

        The response normally includes:

        {
            "mode": "generation",
            "summary": ...,
            "results": ...,
            "updated_records": ...,
            "clean_records": ...
        }

    Raises
    ------
    HTTPException
        Returns status code 400 for invalid request values.

        Returns status code 500 when an unexpected error occurs.
    """
    try:
        file_bytes = await file.read()

        if not file_bytes:
            raise ValueError("Uploaded file is empty.")

        file_type = infer_file_type(file.filename)
        strategy_name = normalize_strategy_name(strategy_name)

        raw_config = parse_config_json(config_json)

        config = validate_and_normalize_config(
            strategy_name=strategy_name,
            config=raw_config,
            mode="generate",
        )

        id_name = clean_optional_string(id_name)
        output_id_field = (
            clean_optional_string(output_id_field)
            or "identifier"
        )

        # Reserve identifiers before generation so the pipeline can avoid
        # creating values that already conflict inside the selected scope.
        reserved_identifiers = (
            get_hard_reserved_identifiers_for_generation(
                session,
                strategy_name=strategy_name,
                project_id=project_id,
            )
        )

        pipeline_result = run_generation_pipeline(
            file_bytes=file_bytes,
            file_type=file_type,
            strategy_name=strategy_name,
            config=config,
            id_name=id_name,
            output_id_field=output_id_field,
            sheet_name=sheet_name,
            reserved_identifiers=reserved_identifiers,
        )

        # Run a final comparison because the database may contain matching
        # identifiers outside the reserved scope or may have changed while the
        # request was being processed.
        pipeline_result = compare_pipeline_result_to_database(
            session,
            pipeline_result=pipeline_result,
            strategy_name=strategy_name,
            project_id=project_id,
        )

        return pipeline_result

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected server error: {error}",
        ) from error