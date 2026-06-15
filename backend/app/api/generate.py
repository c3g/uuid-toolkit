from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from core.pipeline import run_generation_pipeline
from api.utils import (
    infer_file_type,
    parse_config_json,
    clean_optional_string,
    normalize_strategy_name,
    validate_and_normalize_config,
)


router = APIRouter()


@router.post("/generate")
async def generate_identifiers(
    file: UploadFile = File(...),
    strategy_name: str = Form(...),
    config_json: str = Form("{}"),
    id_name: str | None = Form(None),
    output_id_field: str | None = Form(None),
    sheet_name: str | None = Form(None),
) -> dict:
    """
    Generate missing identifiers in an uploaded CSV/JSON file.

    Existing IDs are skipped and left unchanged.

    Form fields
    -----------
    file:
        Uploaded .csv or .json file.

    strategy_name:
        "UUID" or "CPHI".

    config_json:
        UUID example:
            {"version": 4}

        CPHI patient ID with no variant:
            {"project_code": "NRGI", "entity_type": "patient"}

        CPHI sample ID with no variant:
            {"project_code": "NRGI", "entity_type": "sample"}

        CPHI patient ID with variant:
            {"project_code": "NRGI", "entity_type": "patient", "variant": "SPE"}

        CPHI sample ID with variant:
            {"project_code": "NRGI", "entity_type": "sample", "variant": "EXP"}

    id_name:
        Optional existing ID column/key name.

    output_id_field:
        Column/key name to create if no ID column exists.
        Default is "identifier".
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

        # 7. Call generation pipeline
        return run_generation_pipeline(
            file_bytes=file_bytes,
            file_type=file_type,
            strategy_name=strategy_name,
            config=config,
            id_name=id_name,
            output_id_field=output_id_field,
            sheet_name=sheet_name,
        )

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected server error: {error}",
        )