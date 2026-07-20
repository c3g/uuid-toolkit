from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.utils import normalize_strategy_name

from db.database import get_db_session
from db.identifier_repository import(
    find_project_conflicts,
    list_identifiers,
    list_identifiers_by_project,
    list_identifiers_by_strategy,
    save_identifiers_to_project,
)
from db.project_repository import (
    get_or_create_unassigned_project,
    get_project_by_id,
)


router = APIRouter()

class SaveIdentifierRequest(BaseModel):
    """
    Data required to dave clean identifiers to the database
    """
    strategy_name:str
    project_id:int |None = None
    identifiers:list[str]

@router.get("/identifier_database")
def get_identifiers(
    project_id:int |None = None,
    strategy_name: str |None = None,
    session: Session = Depends(get_db_session)
)-> list[dict]:
    if project_id is not None:
        identifiers = list_identifiers_by_project(
            session,
            project_id= project_id
        )
    elif strategy_name is not None:
        identifiers = list_identifiers_by_strategy(
            session,
            strategy_name= strategy_name,
        )
    else:
        identifiers = list_identifiers(session)
    
    return [
        {
            "id": identifier.id,
            "project_id": identifier.project_id,
            "identifier_value": identifier.identifier_value,
            "strategy_name": identifier.strategy_name,
        }
        for identifier in identifiers
    ]

@router.post("/idemtifier_database/save")
def save_clean_identifiers(
    request: SaveIdentifierRequest,
    session: Session = Depends(get_db_session)
) -> dict:
    """
    Save clean identifiers into a selected database project:

    If no project id is assigned or provided, the identifiers will be saved into the Unassigned project for the selected strategy.

    Identifiers that already exist inside the destination project are skipped.
    """
    try:
        strategy_name = normalize_strategy_name(
            request.strategy_name
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error
    cleaned_identifiers = {
        identifier.strip()
        for identifier in request.identifiers
        if identifier.strip()
    }

    if not cleaned_identifiers:
        raise HTTPException(
            status_code=400,
            detail="At lease one non empty clean identifier is required."

        )
    
    if request.project_id is None:
        project = get_or_create_unassigned_project(
            session,
            strategy_name=strategy_name,
        )
    else:
        project = get_project_by_id(
            session,
            project_id=request.project_id,
        )
        if project is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Project with id"
                    f"{request.project_id} was not found"
                )
            )
        if project.strategy_name != strategy_name:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Project '{project.name}' uses strategy"
                    f"'{project.strategy_name}', but the request"
                    f"uses strategy '{strategy_name}'."
                ),
            )
    # Check again because the database may have changed since the
    # user originally validated or generated the identifiers.
    existing_identifiers = find_project_conflicts(
        session,
        project_id=project.id,
        identifiers=cleaned_identifiers,
    )

    identifiers_to_save = (
        cleaned_identifiers - existing_identifiers
    )

    saved_identifiers = []

    if identifiers_to_save:
        try:
            saved_identifiers = save_identifiers_to_project(
                session,
                project_id=project.id,
                strategy_name=strategy_name,
                identifiers=identifiers_to_save,
            )

        except ValueError as error:
            raise HTTPException(
                status_code=409,
                detail=str(error),
            ) from error

    return {
        "project_id": project.id,
        "project_name": project.name,
        "strategy_name": project.strategy_name,

        "submitted_count": len(request.identifiers),
        "unique_identifier_count": len(cleaned_identifiers),

        "saved_count": len(saved_identifiers),
        "already_in_project_count": len(
            existing_identifiers
        ),

        "saved_identifiers": sorted(
            record.identifier_value
            for record in saved_identifiers
        ),

        "already_in_project_identifiers": sorted(
            existing_identifiers
        ),
    }