"""
API route for identifier generation.

This file defines the /generate endpoint. It receives uploaded files and form
data from the frontend, validates the request inputs, and then calls the
generation pipeline.
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session

from core.pipeline import run_generation_pipeline
from api.utils import (
    infer_file_type,
    parse_config_json,
    clean_optional_string,
    normalize_strategy_name,
    validate_and_normalize_config,
)
from db.comparison import (
    compare_pipeline_result_to_database,
    get_hard_reserved_identifiers_for_generation,
)
from db.database import get_db_session


router = APIRouter()


@router.post("/generate")
async def generate_identifiers(
    file: UploadFile = File(...),
    strategy_name: str = Form(...),
    config_json: str = Form("{}"),
    id_name: str | None = Form(None),
    output_id_field: str | None = Form(None),
    sheet_name: str | None = Form(None),
    project_id: int |None = Form(None),
    session: Session = Depends(get_db_session),
) -> dict:
    """
    Generate identifiers from an uploaded file.

    This is the API route for generation requests. It receives the file and form
    data from the frontend, cleans and validates the inputs, and then passes the
    data into the generation pipeline.

    The main idea is:
    - Read the uploaded file.
    - Infer the file type from the filename.
    - Normalize the selected strategy name.
    - Parse config_json into a Python dict.
    - Validate and normalize the config for generation.
    - Clean optional column names.
    - Call run_generation_pipeline.

    This function does not contain the actual generation logic. The real generation
    work is handled inside the pipeline and the selected strategy.

    Form fields
    -----------
    file:
        The uploaded file from the frontend.

        Supported file types depend on infer_file_type, such as:
        - .csv
        - .json
        - .xlsx

    strategy_name:
        The strategy selected by the user.

        Examples:
        - "UUID"
        - "CPHI"
        - "PCGL"
        - "CUSTOM"

    config_json:
        A JSON string containing the config values needed by the selected strategy.

        UUID example:
            {"version": 4}

        CPHI example:
            {"project_code": "NRGI", "entity_type": "sample"}

        PCGL validation/generation example:
            {"project_code": "NRGI", "entity_type": "sample", "variants": ["EXP", "LIB"]}

        Custom example:
            {
                "prefix_mode": "fixed",
                "fixed_prefix": "TEST",
                "connector": "-",
                "suffix_type": "numeric",
                "suffix_length": 6
            }

    id_name:
        Optional name of the column that contains existing identifiers.

        If this is provided, the pipeline will look for identifiers in this column.

    output_id_field:
        Optional name of the column where generated identifiers should be placed.

        If no value is provided, this defaults to "identifier".

    sheet_name:
        Optional sheet name for XLSX files.

        If no sheet name is provided, the parser will use the active sheet.

    Returns
    -------
    dict:
        A dict returned by run_generation_pipeline.

        The response usually contains:

        {
            "mode": "generation",
            "summary": ...,
            "results": ...,
            "updated_records": ...,
            "clean_records": ...
        }

    Raises
    ------
    HTTPException:
        Returns status code 400 if the user input is invalid.

        Returns status code 500 if an unexpected server error occurs.
    """
    try:
        # 1. Read uploaded file
        file_bytes = await file.read()

        if not file_bytes:
            raise ValueError("Uploaded file is empty.")

        # 2. Infer file type from filename extension
        file_type = infer_file_type(file.filename)

        # 3. Normalize strategy name
        strategy_name = normalize_strategy_name(strategy_name)

        # 4. Convert config_json string into Python dict
        raw_config = parse_config_json(config_json)

        # 5. Validate and normalize config
        # For CPHI:
        # - entity_type is required
        # - variant is optional
        config = validate_and_normalize_config(
            strategy_name=strategy_name,
            config=raw_config,
            mode="generate",
        )

        # 6. Clean optional field names
        id_name = clean_optional_string(id_name)
        output_id_field = clean_optional_string(output_id_field) or "identifier"

        #7. Get database identifiers under scope indicated
        reserved_identifiers = (
            get_hard_reserved_identifiers_for_generation(
                session,
                strategy_name=strategy_name,
                project_id=project_id,
            )
        )

        #8. Run generation pipeline

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

        #9. Compare final generated results against the database
        # This adds the following:
        # - marks remaining hard conflicts meaning overlap under the scope indicated
        # - adds soft warnings for overlaps outside of scope
        # - rebuilds clean_records and final summary

        pipeline_result = compare_pipeline_result_to_database(
            session,
            pipeline_result=pipeline_result,
            strategy_name=strategy_name,
            project_id=project_id,
        )

        #10. Return final pipeline result after database check
        
        return pipeline_result

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected server error: {error}",
        )