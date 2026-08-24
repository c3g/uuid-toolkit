"""
API route for listing database projects.

This file defines the ``GET /projects`` endpoint used by the frontend when it
needs Project Tag options.

The endpoint can return:

- Every project when no strategy is selected.
- Only projects belonging to one strategy when ``strategy_name`` is provided.

How this file connects to the project
-------------------------------------
- ``projectsApi.js`` calls this endpoint.
- ``ToolkitPage.jsx`` uses the response for the Project Tag selector.
- ``DatabaseManagementPage.jsx`` uses it for filtering and displaying project
  names.
- ``db/project_repository.py`` contains the database query that returns the
  project records.
- ``db/database.py`` provides the SQLAlchemy session.

Adding a new strategy
---------------------
This file normally does not need to change when a new strategy is added.
Projects store the strategy name as a database value, so this endpoint can
return projects for any strategy.

The new strategy still needs to be added to the backend strategy registry,
API config validation, frontend strategy selector, config controls, and tests.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.auth_dependencies import require_authenticated_user
from db.database import get_db_session
from db.project_repository import list_projects


router = APIRouter(
    prefix="/projects",
    tags=["projects"],
    dependencies=[Depends(require_authenticated_user)],
)


@router.get("")
def get_projects(
    strategy_name: str | None = Query(None),
    session: Session = Depends(get_db_session),
) -> list[dict]:
    """
    Return projects with an optional strategy filter.

    Parameters
    ----------
    strategy_name:
        Optional strategy name used to filter the projects. The value is
        stripped and converted to uppercase before comparison.

        Examples:

        - ``UUID``
        - ``CPHI``
        - ``PCGL``
        - ``CUSTOM``

    session:
        Database session provided by ``get_db_session()``.

    Returns
    -------
    list[dict]
        Project records formatted for the frontend:

        {
            "id": int,
            "name": str,
            "strategy_name": str,
            "description": str | None,
        }

    Notes
    -----
    The current implementation first loads the projects and then applies the
    optional strategy filter in Python. If the number of projects becomes much
    larger, the filtering can be moved into ``project_repository.py`` so the
    database performs it directly.
    """
    projects = list_projects(session)

    if strategy_name is not None:
        cleaned_strategy_name = (
            strategy_name.strip().upper()
        )

        projects = [
            project
            for project in projects
            if project.strategy_name
            == cleaned_strategy_name
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