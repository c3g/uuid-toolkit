from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Query,
)
from sqlalchemy.orm import Session

from db.database import get_db_session
from db.database_management import (
    clear_all_table_data,
    create_project,
    delete_identifier_by_id,
    delete_identifiers_by_project,
    delete_identifiers_by_strategy,
    delete_project_by_id,
    delete_projects_by_strategy,
)


router = APIRouter(
    prefix="/database-management",
    tags=["database management"],
)


def require_confirmation(confirm: bool) -> None:
    if confirm is not True:
        raise HTTPException(
            status_code=400,
            detail="Set confirm=true to perform this deletion.",
        )


@router.post("/projects")
def add_project(
    name: str = Form(...),
    strategy_name: str = Form(...),
    description: str | None = Form(None),
    session: Session = Depends(get_db_session),
) -> dict:
    try:
        project = create_project(
            session,
            name=name,
            strategy_name=strategy_name,
            description=description,
        )

        return {
            "id": project.id,
            "name": project.name,
            "strategy_name": project.strategy_name,
            "description": project.description,
        }
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error


@router.delete("/identifiers/row/{identifier_id}")
def remove_identifier_row(
    identifier_id: int,
    confirm: bool = Query(False),
    session: Session = Depends(get_db_session),
) -> dict:
    require_confirmation(confirm)

    deleted = delete_identifier_by_id(
        session,
        identifier_id=identifier_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Identifier row {identifier_id} was not found.",
        )

    return {
        "identifier_id": identifier_id,
        "deleted": True,
    }


@router.delete("/identifiers/project/{project_id}")
def remove_project_identifiers(
    project_id: int,
    confirm: bool = Query(False),
    session: Session = Depends(get_db_session),
) -> dict:
    require_confirmation(confirm)

    deleted_count = delete_identifiers_by_project(
        session,
        project_id=project_id,
    )

    return {
        "project_id": project_id,
        "identifiers_deleted": deleted_count,
    }


@router.delete("/identifiers/strategy/{strategy_name}")
def remove_strategy_identifiers(
    strategy_name: str,
    confirm: bool = Query(False),
    session: Session = Depends(get_db_session),
) -> dict:
    require_confirmation(confirm)

    deleted_count = delete_identifiers_by_strategy(
        session,
        strategy_name=strategy_name,
    )

    return {
        "strategy_name": strategy_name.strip().upper(),
        "identifiers_deleted": deleted_count,
    }


@router.delete("/projects/{project_id}")
def remove_project(
    project_id: int,
    confirm: bool = Query(False),
    session: Session = Depends(get_db_session),
) -> dict:
    require_confirmation(confirm)

    result = delete_project_by_id(
        session,
        project_id=project_id,
    )

    if result["project_deleted"] is not True:
        raise HTTPException(
            status_code=404,
            detail=f"Project {project_id} was not found.",
        )

    return {
        "project_id": project_id,
        **result,
    }


@router.delete("/projects/strategy/{strategy_name}")
def remove_projects_for_strategy(
    strategy_name: str,
    confirm: bool = Query(False),
    session: Session = Depends(get_db_session),
) -> dict:
    require_confirmation(confirm)

    result = delete_projects_by_strategy(
        session,
        strategy_name=strategy_name,
    )

    return {
        "strategy_name": strategy_name.strip().upper(),
        **result,
    }


@router.delete("/all-data")
def remove_all_data(
    confirm: bool = Query(False),
    session: Session = Depends(get_db_session),
) -> dict:
    require_confirmation(confirm)

    result = clear_all_table_data(session)

    return {
        "deleted": True,
        **result,
    }