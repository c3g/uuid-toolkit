from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import get_db_session
from db.identifier_repository import(
    list_identifiers,
    list_identifiers_by_project,
    list_identifiers_by_strategy,
)


router = APIRouter()

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