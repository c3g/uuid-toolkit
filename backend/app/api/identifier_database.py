"""
API routes for viewing and saving identifiers in the database.

This file handles two parts of the database workflow:

- Returning stored identifiers for the Database Management page.
- Saving clean identifiers after validation or generation.

The actual database queries stay inside the repository files. This router
handles request validation, project selection, and HTTP responses.

How this file connects to the project
-------------------------------------
- ``ToolkitPage.jsx`` sends clean identifiers to the save endpoint.
- ``DatabaseManagementPage.jsx`` loads identifiers from the GET endpoint.
- ``identifiersApi.js`` contains the frontend requests for these routes.
- ``api/utils.py`` normalizes the selected strategy name.
- ``db/identifier_repository.py`` reads and saves identifier records.
- ``db/project_repository.py`` finds the selected project or creates an
  Unassigned project when no project is selected.
- ``db/database.py`` provides the SQLAlchemy session.

Adding a new strategy
---------------------
This file normally does not need to change when a new strategy is added because
identifiers are stored using the strategy name as a regular database value.

For a new strategy, update the strategy class, registry, API config validation,
frontend controls, and tests. This file only needs changes if the strategy uses
a different database-saving workflow.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.utils import normalize_strategy_name
from db.database import get_db_session
from db.identifier_repository import (
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
    Request body used to save clean identifiers.

    ``project_id`` is optional. When it is missing, the identifiers are saved
    under the Unassigned project for the selected strategy.
    """

    strategy_name: str
    project_id: int | None = None
    identifiers: list[str]


@router.get("/identifier_database")
def get_identifiers(
    project_id: int | None = None,
    strategy_name: str | None = None,
    session: Session = Depends(get_db_session),
) -> list[dict]:
    """
    Return stored identifiers using an optional project or strategy filter.

    Filtering priority:

    1. When ``project_id`` is provided, return identifiers from that project.
    2. Otherwise, when ``strategy_name`` is provided, return identifiers from
       that strategy.
    3. When neither is provided, return every stored identifier.

    Parameters
    ----------
    project_id:
        Optional project used to filter the identifier records.

    strategy_name:
        Optional strategy used when no project filter is provided.

    session:
        Database session provided by ``get_db_session()``.

    Returns
    -------
    list[dict]
        Stored identifier records formatted for the frontend.
    """
    if project_id is not None:
        identifiers = list_identifiers_by_project(
            session,
            project_id=project_id,
        )

    elif strategy_name is not None:
        identifiers = list_identifiers_by_strategy(
            session,
            strategy_name=strategy_name,
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


@router.post("/identifier_database/save")
def save_clean_identifiers(
    request: SaveIdentifierRequest,
    session: Session = Depends(get_db_session),
) -> dict:
    """
    Save clean identifiers into a project.

    The submitted identifiers are stripped, empty values are removed, and
    duplicates inside the request are collapsed before saving.

    When ``project_id`` is missing, the identifiers are saved under the
    Unassigned project for the selected strategy.

    Identifiers already stored in the destination project are skipped. This
    check is repeated here because the database may have changed after the
    original validation or generation request finished.

    Parameters
    ----------
    request:
        Strategy name, optional project ID, and clean identifiers to save.

    session:
        Database session provided by ``get_db_session()``.

    Returns
    -------
    dict
        Save summary containing the selected project, submitted counts, saved
        identifiers, and identifiers that were already in the project.

    Raises
    ------
    HTTPException
        Returns status code 400 when the strategy or submitted identifiers are
        invalid.

        Returns status code 404 when the selected project does not exist.

        Returns status code 409 when the repository reports a database
        conflict while saving.
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
            detail=(
                "At least one non-empty clean identifier "
                "is required."
            ),
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
                    f"Project with id {request.project_id} "
                    "was not found."
                ),
            )

        if project.strategy_name != strategy_name:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Project '{project.name}' uses strategy "
                    f"'{project.strategy_name}', but the request "
                    f"uses strategy '{strategy_name}'."
                ),
            )

    # Check again at save time in case another request added one of these
    # identifiers after the original validation or generation finished.
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