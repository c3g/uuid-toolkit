from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.database import get_db_session
from db.project_repository import list_projects


router = APIRouter(
    prefix="/projects",
    tags=["projects"],
)


@router.get("")
def get_projects(
    strategy_name: str | None = Query(None),
    session: Session = Depends(get_db_session),
) -> list[dict]:
    projects = list_projects(session)

    if strategy_name is not None:
        cleaned_strategy_name = strategy_name.strip().upper()

        projects = [
            project
            for project in projects
            if project.strategy_name == cleaned_strategy_name
        ]

    return [
        {
            "id": project.id,
            "name": project.name,
            "strategy_name": project.strategy_name,
            "description": project.description,
        }
        for project in projects
    ]