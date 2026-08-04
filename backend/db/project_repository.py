"""
Repository functions for Project records.

This file contains the database queries used to create, list, and find Project
Tags. It also creates the default ``Unassigned`` project used when identifiers
are saved without a selected Project Tag.

How this file connects to the project
-------------------------------------
- ``api/projects.py`` uses ``list_projects()`` for the Project Tag dropdowns.
- ``api/identifier_database.py`` uses ``get_project_by_id()`` and
  ``get_or_create_unassigned_project()`` when saving clean identifiers.
- ``db/comparison.py`` uses ``get_project_by_id()`` to confirm that a selected
  project exists and belongs to the requested strategy.
- ``db/models.py`` defines the ``Project`` table.
- ``db/database.py`` provides the SQLAlchemy session.

Project creation from the Database Management API currently uses
``db/database_management.py``. The ``create_project()`` function in this file
is a smaller repository helper that can be used when project creation does not
need the extra checks handled by that service.

Adding a new strategy
---------------------
This file normally does not need to change when a new strategy is added.
Projects store the strategy name as a regular string, so the same queries work
for any registered strategy.

The new strategy still needs to be added to ``registry.py``, ``api/utils.py``,
the frontend strategy controls, and the related tests.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import Project


def create_project(
    session: Session,
    *,
    name: str,
    strategy_name: str,
    description: str,
) -> Project:
    """
    Create and save one Project record.

    Parameters
    ----------
    session:
        Active SQLAlchemy session.

    name:
        Project name shown to the user.

    strategy_name:
        Identifier strategy associated with the project.

    description:
        Project description.

    Returns
    -------
    Project
        Newly created and refreshed project record.

    Notes
    -----
    This function does not check whether another project already uses the same
    name and strategy. The database unique constraint is still the final
    safeguard against duplicates.
    """
    project = Project(
        name=name,
        strategy_name=strategy_name,
        description=description,
    )

    session.add(project)
    session.commit()
    session.refresh(project)

    return project


def list_projects(
    session: Session,
) -> list[Project]:
    """
    Return every project ordered by database row ID.

    The API layer may apply an additional strategy filter after receiving this
    list.
    """
    statement = (
        select(Project)
        .order_by(Project.id)
    )

    result = session.execute(statement)

    return list(result.scalars().all())


def get_project_by_id(
    session: Session,
    *,
    project_id: int,
) -> Project | None:
    """
    Return one project by its database ID.

    Returns ``None`` when the project does not exist.
    """
    statement = (
        select(Project)
        .where(Project.id == project_id)
    )

    result = session.execute(statement)

    return result.scalar_one_or_none()


def get_project_by_name(
    session: Session,
    *,
    name: str,
    strategy_name: str,
) -> Project | None:
    """
    Find a project using its name and strategy.

    Project names are only unique within the same strategy, so both values are
    required for the lookup.

    Returns ``None`` when no matching project exists.
    """
    statement = (
        select(Project)
        .where(Project.name == name)
        .where(
            Project.strategy_name == strategy_name
        )
    )

    result = session.execute(statement)

    return result.scalar_one_or_none()


def get_or_create_unassigned_project(
    session: Session,
    *,
    strategy_name: str,
) -> Project:
    """
    Return the Unassigned project for a strategy, creating it when needed.

    Each strategy receives its own Unassigned project because project names are
    unique only within the same strategy.

    This function is used when clean identifiers are saved without a selected
    Project Tag.

    Parameters
    ----------
    session:
        Active SQLAlchemy session.

    strategy_name:
        Strategy that should own the Unassigned project.

    Returns
    -------
    Project
        Existing or newly created Unassigned project.
    """
    statement = (
        select(Project)
        .where(Project.name == "Unassigned")
        .where(
            Project.strategy_name == strategy_name
        )
    )

    existing_project = (
        session.execute(statement)
        .scalar_one_or_none()
    )

    if existing_project is not None:
        return existing_project

    project = Project(
        name="Unassigned",
        strategy_name=strategy_name,
        description=(
            "Default project for "
            f"{strategy_name} identifiers saved without "
            "a selected Project Tag."
        ),
    )

    session.add(project)
    session.commit()
    session.refresh(project)

    return project