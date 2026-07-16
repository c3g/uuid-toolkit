"""
API route for identifier validation.

This file defines the /validate endpoint. It receives uploaded files and form
data from the frontend, validates the request inputs, and then calls the
validation pipeline.
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session

from db.comparison import compare_pipeline_result_to_database
from db.database import get_db_session

from core.pipeline import run_validation_pipeline
from api.utils import (
    infer_file_type,
    parse_config_json,
    clean_optional_string,
    normalize_strategy_name,
    validate_and_normalize_config,
)

router = APIRouter()

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

    This is the API route for validation requests. It receives the file and form
    data from the frontend, cleans and validates the inputs, and then passes the
    data into the validation pipeline.

    The main idea is:
    - Read the uploaded file.
    - Check that the file is not empty.
    - Infer the file type from the filename.
    - Normalize the selected strategy name.
    - Parse config_json into a Python dict.
    - Validate and normalize the config for validation.
    - Clean the optional ID column name.
    - Call run_validation_pipeline.

    This function does not contain the actual identifier validation logic. The real
    validation work is handled inside the pipeline and the selected strategy.

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

        PCGL example:
            {"project_code": "NRGI", "entity_type": "sample", "variant": "EXP"}

        Custom example:
            {
                "prefix_mode": "fixed",
                "fixed_prefix": "TEST",
                "connector": "-",
                "suffix_type": "numeric",
                "suffix_length": 6
            }

    id_name:
        Optional name of the column that contains the identifiers to validate.

        If this is provided, the pipeline will validate identifiers from this column.

    sheet_name:
        Optional sheet name for XLSX files.

        If no sheet name is provided, the parser will use the active sheet.

    Returns
    -------
    dict:
        A dict returned by run_validation_pipeline.

        The response usually contains:

        {
            "mode": "validation",
            "summary": ...,
            "results": ...,
            "clean_records": ...
        }

    Raises
    ------
    HTTPException:
        Returns status code 400 if the user input is invalid.

        Returns status code 500 if an unexpected server error occurs.
    """
    try:
        file_bytes = await file.read()

        if not file_bytes:
            raise ValueError("File is empty.")
        
        file_type = infer_file_type(file.filename)
        
        strategy_name = normalize_strategy_name(strategy_name)

        raw_config = parse_config_json(config_json)

        config = validate_and_normalize_config(strategy_name=strategy_name, config=raw_config, mode = "validate",)

        id_name = clean_optional_string(id_name)

        pipeline_result = run_validation_pipeline(
            file_bytes=file_bytes,
            file_type=file_type,
            strategy_name=strategy_name,
            config=config,
            id_name=id_name,
            sheet_name=sheet_name,
        )

        pipeline_result = compare_pipeline_result_to_database(
            session,
            pipeline_result=pipeline_result,
            strategy_name=strategy_name,
            project_id=project_id,
        )

        return  pipeline_result
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected server error: {error}",
        )