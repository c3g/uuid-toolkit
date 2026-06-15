from fastapi import APIRouter, UploadFile, File, Form, HTTPException

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
) -> dict:
    try:
        file_bytes = await file.read()

        if not file_bytes:
            raise ValueError("File is empty.")
        
        file_type = infer_file_type(file.filename)
        
        strategy_name = normalize_strategy_name(strategy_name)

        raw_config = parse_config_json(config_json)

        config = validate_and_normalize_config(strategy_name=strategy_name, config=raw_config, mode = "validate",)

        id_name = clean_optional_string(id_name)

        return run_validation_pipeline(
            file_bytes=file_bytes,
            file_type=file_type,
            strategy_name=strategy_name,
            config=config,
            id_name=id_name,
            sheet_name=sheet_name,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected server error: {error}",
        )