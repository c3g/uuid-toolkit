"""
API routes for creating projects and managing stored identifier data.

This router exposes the database-management endpoints used by the frontend.
It handles request values, confirmation checks, and HTTP responses, while the
actual database operations stay inside ``db/database_management.py``.

Main connections
----------------
- ``db/database.py`` provides one SQLAlchemy session per request.
- ``db/database_management.py`` contains the create and delete operations.
- ``projectsApi.js`` uses the project creation endpoint.
- ``identifiersApi.js`` uses the identifier deletion endpoints.
- ``DatabaseManagementPage.jsx`` provides the user-facing controls for these
  actions.

Deletion behavior
-----------------
All delete endpoints require ``confirm=true``. This prevents destructive
operations from running through an accidental or incomplete request.

Identifier-only deletion keeps project records in the database. Project and
all-data deletion are separate operations because they remove more than stored
identifier rows.

Adding a new strategy
---------------------
This file normally does not need to change when a new strategy is added.
Projects and identifiers store ``strategy_name`` as a regular value, so the
same routes can manage records for any registered strategy.

A change is only needed here when a new strategy requires a new type of
database-management action or different deletion rules. Normal strategy setup
still belongs in the strategy registry, API config validation, frontend config
controls, and tests.
"""

from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Query,
)
from sqlalchemy.orm import Session

from core.auth_dependencies import require_admin
from db.database import get_db_session
from db.database_management import (
    clear_all_table_data,
    create_project,
    delete_all_identifiers,
    delete_identifier_by_id,
    delete_identifiers_by_project,
    delete_identifiers_by_strategy,
    delete_identifiers_by_value,
    delete_project_by_id,
    delete_projects_by_strategy,
)


router = APIRouter(
    prefix="/database-management",
    tags=["database management"],
    dependencies=[Depends(require_admin)],
)


def require_confirmation(confirm: bool) -> None:
    """
    Require explicit confirmation before running a delete operation.

    Parameters
    ----------
    confirm:
        Query value sent by the client. It must be ``True`` for the request to
        continue.

    Raises
    ------
    HTTPException
        Raised with status code 400 when confirmation was not provided.
    """
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
    """
    Create a project for one identifier strategy.

    The repository layer cleans and validates the project values before saving
    the record.

    Parameters
    ----------
    name:
        User-facing project name.

    strategy_name:
        Identifier strategy associated with the project.

    description:
        Optional project description.

    session:
        Database session provided by ``get_db_session()``.

    Returns
    -------
    dict
        The newly created project.

    Raises
    ------
    HTTPException
        Returns status code 400 when the project values are invalid or conflict
        with an existing project.
    """
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
    """
    Delete one identifier record using its database row ID.

    This removes only the selected identifier row. Its project remains in the
    database.

    Raises
    ------
    HTTPException
        Returns status code 400 when confirmation is missing.
        Returns status code 404 when the identifier row does not exist.
    """
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


@router.delete("/identifiers/value")
def remove_identifiers_by_value(
    identifier_value: str = Query(...),
    project_id: int | None = Query(None),
    confirm: bool = Query(False),
    session: Session = Depends(get_db_session),
) -> dict:
    """
    Delete records that exactly match one identifier value.

    When ``project_id`` is provided, only matching records inside that project
    are deleted. Without a project ID, every exact match is deleted.

    Parameters
    ----------
    identifier_value:
        Exact identifier value to remove.

    project_id:
        Optional project scope for the deletion.

    Raises
    ------
    HTTPException
        Returns status code 400 when confirmation or the identifier value is
        invalid.
        Returns status code 404 when no matching record is found.
    """
    require_confirmation(confirm)

    try:
        deleted_count = delete_identifiers_by_value(
            session,
            identifier_value=identifier_value,
            project_id=project_id,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    if deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Identifier '{identifier_value.strip()}' "
                "was not found."
            ),
        )

    return {
        "identifier_value": identifier_value.strip(),
        "project_id": project_id,
        "identifiers_deleted": deleted_count,
    }


@router.delete("/identifiers/project/{project_id}")
def remove_project_identifiers(
    project_id: int,
    confirm: bool = Query(False),
    session: Session = Depends(get_db_session),
) -> dict:
    """
    Delete every identifier stored under one project.

    The project record itself is kept so it can still be used for future
    validation, generation, and identifier storage.
    """
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
    """
    Delete every identifier stored under one strategy.

    Project records are kept. This route only clears identifier rows belonging
    to the selected strategy.
    """
    require_confirmation(confirm)

    deleted_count = delete_identifiers_by_strategy(
        session,
        strategy_name=strategy_name,
    )

    return {
        "strategy_name": strategy_name.strip().upper(),
        "identifiers_deleted": deleted_count,
    }


@router.delete("/identifiers/all")
def remove_all_identifiers(
    confirm: bool = Query(False),
    session: Session = Depends(get_db_session),
) -> dict:
    """
    Delete all stored identifiers while keeping every project.

    This endpoint is used by the user-facing Clear All Identifiers action.
    It is separate from ``/all-data`` because project records should remain
    available after the identifier registry is cleared.
    """
    require_confirmation(confirm)

    deleted_count = delete_all_identifiers(session)

    return {
        "deleted": True,
        "identifiers_deleted": deleted_count,
        "projects_deleted": 0,
    }


@router.delete("/projects/{project_id}")
def remove_project(
    project_id: int,
    confirm: bool = Query(False),
    session: Session = Depends(get_db_session),
) -> dict:
    """
    Delete one project and any identifier rows connected to it.

    This operation is more destructive than clearing a project's identifiers
    because the project record itself is also removed.

    Raises
    ------
    HTTPException
        Returns status code 404 when the project does not exist.
    """
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
    """
    Delete all projects and identifiers belonging to one strategy.

    This is intended for administrative cleanup rather than the normal
    identifier-management workflow.
    """
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
    """
    Delete all stored identifiers and all project records.

    This is the most destructive route in this router. It should remain
    separate from the normal Clear All Identifiers action and should be
    protected by backend authorization before production deployment.
    """
    require_confirmation(confirm)

    result = clear_all_table_data(session)

    return {
        "deleted": True,
        **result,
    }