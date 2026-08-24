"""
API route for identifier validation.

This file defines the ``POST /validate`` endpoint used by the toolkit page. It
receives the uploaded file and form data, prepares the request values, runs the
validation pipeline, and then compares the valid identifiers with the database.

The request flow is:

    ToolkitPage.jsx
        -> POST /validate
        -> api/utils.py
        -> core/pipeline.py
        -> registry.py
        -> selected strategy
        -> db/comparison.py
        -> response returned to the frontend

How this file connects to the project
-------------------------------------
- ``ToolkitPage.jsx`` sends the file, strategy, config, ID column, optional
  worksheet, and selected Project Tag.
- ``api/utils.py`` cleans and validates request values before the pipeline runs.
- ``run_validation_pipeline()`` parses the file and validates each identifier
  using the strategy returned by ``registry.py``.
- ``compare_pipeline_result_to_database()`` adds hard conflicts and soft
  warnings based on the selected database scope.
- ``get_db_session()`` provides the SQLAlchemy session used for database checks.

Adding a new strategy
---------------------
This route normally does not need a separate branch for a new strategy because
the strategy name and config are passed through the shared utility, registry,
and pipeline layers.

For a new strategy, update:

1. The strategy class and ``registry.py``.
2. ``api/utils.py`` so the config is validated and normalized.
3. ``ConfigPanel.jsx`` with the strategy option and controls.
4. ``ToolkitPage.jsx`` so ``buildConfig()`` sends the required values.
5. Validation and pipeline tests.

This route only needs a direct change when a strategy requires a new form field
that cannot be included inside ``config_json``.
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
from core.pipeline import run_validation_pipeline
from db.comparison import compare_pipeline_result_to_database
from db.database import get_db_session


router = APIRouter(
    dependencies=[Depends(require_authenticated_user)],
)


@router.post("/validate")
async def validate_identifiers(
    file: UploadFile = File(...),
    strategy_name: str = Form(...),
    config_json: str = Form("{}"),
    id_name: str | None = Form(None),
    sheet_name: str | None = Form(None),
    project_id: int | None = Form(None),
    session: Session = Depends(get_db_session),
) -> dict:
    """
    Validate identifiers from an uploaded file.

    The route prepares the request, runs the validation pipeline, and then
    compares the pipeline result with identifiers already stored in the
    database.

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

        PCGL example:

            {
                "project_code": "NRGI",
                "entity_type": "sample",
                "variant": "EXP"
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
        Optional name of the column containing the identifiers to validate. The
        pipeline chooses the identifier column when no value is provided.

    sheet_name:
        Optional worksheet name for XLSX uploads. The parser uses the active
        worksheet when no name is provided.

    project_id:
        Optional database project used to define the comparison scope.

        A duplicate inside the selected project is treated as a hard conflict.
        Matching identifiers in other projects under the same strategy may be
        returned as soft warnings.

        When no project is selected, the comparison uses the strategy-wide
        scope.

    session:
        Database session provided by ``get_db_session()``.

    Returns
    -------
    dict
        Final validation result after the pipeline and database comparison.

        The response normally includes:

        {
            "mode": "validation",
            "summary": ...,
            "results": ...,
            "updated_records": ...,
            "clean_records": ...
        }

    Raises
    ------
    HTTPException
        Returns status code 400 when the uploaded file, strategy, config, or
        other request values are invalid.

        Returns status code 500 when an unexpected server error occurs.

    Notes
    -----
    This route does not contain identifier-format rules. Those rules belong to
    the concrete strategy classes selected through ``registry.py``.

    It also does not contain the database comparison queries. Those checks are
    handled by ``db/comparison.py`` after normal strategy validation finishes.
    """
    try:
        file_bytes = await file.read()

        if not file_bytes:
            raise ValueError("Uploaded file is empty.")

        file_type = infer_file_type(file.filename)
        strategy_name = normalize_strategy_name(
            strategy_name
        )

        raw_config = parse_config_json(config_json)

        config = validate_and_normalize_config(
            strategy_name=strategy_name,
            config=raw_config,
            mode="validate",
        )

        id_name = clean_optional_string(id_name)

        pipeline_result = run_validation_pipeline(
            file_bytes=file_bytes,
            file_type=file_type,
            strategy_name=strategy_name,
            config=config,
            id_name=id_name,
            sheet_name=sheet_name,
        )

        # Strategy validation only checks the identifier format. This final
        # comparison adds database conflicts and warnings to the same result.
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