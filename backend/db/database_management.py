"""
Database write and deletion operations.

This module contains the database operations used by the
``database_management`` API router. It creates Project Tags and performs
identifier or project deletion using SQLAlchemy 2.0 statements.

The API layer is responsible for request validation, HTTP status codes, and
confirmation checks. This file is responsible for database transactions,
commits, rollbacks, and deleted-row counts.

How this file connects to the project
-------------------------------------
- ``api/database_management.py`` calls the functions in this module.
- ``db/models.py`` defines ``Project`` and ``IdentifierRegistry``.
- ``db/database.py`` provides the SQLAlchemy session.
- ``DatabaseManagementPage.jsx`` triggers the related frontend actions through
  ``projectsApi.js`` and ``identifiersApi.js``.
- ``db/project_repository.py`` handles project lookup and listing operations.
- ``db/identifier_repository.py`` handles identifier lookup, comparison, and
  saving operations.

Adding a new strategy
---------------------
This file normally does not need to change when a strategy is added. Projects
and identifiers store ``strategy_name`` as a regular value, so these operations
work for every registered strategy.

A change is only needed when a new strategy requires different database
deletion rules or additional stored tables. Normal strategy setup belongs in
the strategy class, ``registry.py``, ``api/utils.py``, frontend config files,
and tests.
"""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.models import IdentifierRegistry, Project


def _safe_rowcount(
    rowcount: int | None,
) -> int:
    """
    Convert SQLAlchemy's optional row count into a safe non-negative integer.

    Some database drivers may return ``None`` or a negative value when the
    affected-row count is unavailable.
    """
    if rowcount is None or rowcount < 0:
        return 0

    return rowcount


def create_project(
    session: Session,
    *,
    name: str,
    strategy_name: str,
    description: str | None = None,
) -> Project:
    """
    Create one Project Tag for an identifier strategy.

    Project names must be unique within the same strategy. The same name may
    therefore exist once under CPHI, once under PCGL, and so on.

    Parameters
    ----------
    session:
        Active SQLAlchemy session.

    name:
        User-facing project name.

    strategy_name:
        Strategy associated with the project.

    description:
        Optional project description.

    Returns
    -------
    Project
        Newly created and refreshed project record.

    Raises
    ------
    ValueError
        Raised when required values are empty or the project conflicts with an
        existing project.
    """
    cleaned_name = name.strip()
    cleaned_strategy_name = strategy_name.strip()

    if not cleaned_name:
        raise ValueError(
            "Project name cannot be empty."
        )

    if not cleaned_strategy_name:
        raise ValueError(
            "Strategy name cannot be empty."
        )

    existing_statement = (
        select(Project)
        .where(Project.name == cleaned_name)
        .where(
            Project.strategy_name
            == cleaned_strategy_name
        )
    )

    existing_project = session.execute(
        existing_statement
    ).scalar_one_or_none()

    if existing_project is not None:
        raise ValueError(
            f"Project '{cleaned_name}' already exists "
            f"under strategy '{cleaned_strategy_name}'."
        )

    project = Project(
        name=cleaned_name,
        strategy_name=cleaned_strategy_name,
        description=(
            description.strip()
            if description
            else None
        ),
    )

    try:
        session.add(project)
        session.commit()
        session.refresh(project)

    except IntegrityError as error:
        session.rollback()

        raise ValueError(
            "The project could not be created because it "
            "conflicts with an existing project."
        ) from error

    return project


def delete_identifier_by_id(
    session: Session,
    *,
    identifier_id: int,
) -> bool:
    """
    Delete one identifier using its database row ID.

    Returns
    -------
    bool
        ``True`` when a row was deleted and ``False`` when the row did not
        exist.
    """
    try:
        result = session.execute(
            delete(IdentifierRegistry).where(
                IdentifierRegistry.id
                == identifier_id
            )
        )

        session.commit()

    except Exception:
        session.rollback()
        raise

    return _safe_rowcount(result.rowcount) > 0


def delete_identifiers_by_value(
    session: Session,
    *,
    identifier_value: str,
    project_id: int | None = None,
) -> int:
    """
    Delete rows that exactly match one identifier value.

    When ``project_id`` is provided, only matches inside that project are
    removed. Without a project ID, exact matches across all projects are
    removed.

    Returns
    -------
    int
        Number of identifier rows deleted.

    Raises
    ------
    ValueError
        Raised when the identifier value is empty.
    """
    cleaned_identifier_value = (
        identifier_value.strip()
    )

    if not cleaned_identifier_value:
        raise ValueError(
            "Identifier value cannot be empty."
        )

    statement = delete(
        IdentifierRegistry
    ).where(
        IdentifierRegistry.identifier_value
        == cleaned_identifier_value
    )

    if project_id is not None:
        statement = statement.where(
            IdentifierRegistry.project_id
            == project_id
        )

    try:
        result = session.execute(statement)
        session.commit()

    except Exception:
        session.rollback()
        raise

    return _safe_rowcount(result.rowcount)


def delete_identifiers_by_project(
    session: Session,
    *,
    project_id: int,
) -> int:
    """
    Delete every identifier belonging to one project.

    The Project Tag itself remains in the database.

    Returns
    -------
    int
        Number of identifier rows deleted.
    """
    try:
        result = session.execute(
            delete(IdentifierRegistry).where(
                IdentifierRegistry.project_id
                == project_id
            )
        )

        session.commit()

    except Exception:
        session.rollback()
        raise

    return _safe_rowcount(result.rowcount)


def delete_identifiers_by_strategy(
    session: Session,
    *,
    strategy_name: str,
) -> int:
    """
    Delete every identifier stored under one strategy.

    Project Tags remain available after the identifiers are removed.

    Returns
    -------
    int
        Number of identifier rows deleted.
    """
    cleaned_strategy_name = (
        strategy_name.strip()
    )

    try:
        result = session.execute(
            delete(IdentifierRegistry).where(
                IdentifierRegistry.strategy_name
                == cleaned_strategy_name
            )
        )

        session.commit()

    except Exception:
        session.rollback()
        raise

    return _safe_rowcount(result.rowcount)


def delete_all_identifiers(
    session: Session,
) -> int:
    """
    Delete every identifier row while keeping projects and database tables.

    Returns
    -------
    int
        Number of identifier rows deleted.
    """
    try:
        result = session.execute(
            delete(IdentifierRegistry)
        )

        session.commit()

    except Exception:
        session.rollback()
        raise

    return _safe_rowcount(result.rowcount)


def delete_project_by_id(
    session: Session,
    *,
    project_id: int,
) -> dict[str, int | bool]:
    """
    Delete one project and all identifiers belonging to it.

    Both deletions use the same transaction. If either operation fails, the
    transaction is rolled back.

    Returns
    -------
    dict[str, int | bool]
        Whether the project was deleted and how many identifier rows were
        removed.
    """
    project = session.get(
        Project,
        project_id,
    )

    if project is None:
        return {
            "project_deleted": False,
            "identifiers_deleted": 0,
        }

    try:
        identifier_result = session.execute(
            delete(IdentifierRegistry).where(
                IdentifierRegistry.project_id
                == project_id
            )
        )

        project_result = session.execute(
            delete(Project).where(
                Project.id == project_id
            )
        )

        session.commit()

    except Exception:
        session.rollback()
        raise

    return {
        "project_deleted": (
            _safe_rowcount(
                project_result.rowcount
            )
            > 0
        ),
        "identifiers_deleted": _safe_rowcount(
            identifier_result.rowcount
        ),
    }


def delete_projects_by_strategy(
    session: Session,
    *,
    strategy_name: str,
) -> dict[str, int]:
    """
    Delete all projects under one strategy and their identifiers.

    The identifiers are removed first so both operations can complete safely
    inside the same transaction.

    Returns
    -------
    dict[str, int]
        Number of deleted projects and identifier rows.
    """
    cleaned_strategy_name = (
        strategy_name.strip().upper()
    )

    project_ids_statement = (
        select(Project.id)
        .where(
            Project.strategy_name
            == cleaned_strategy_name
        )
    )

    project_ids = set(
        session.execute(
            project_ids_statement
        ).scalars().all()
    )

    if not project_ids:
        return {
            "projects_deleted": 0,
            "identifiers_deleted": 0,
        }

    try:
        identifier_result = session.execute(
            delete(IdentifierRegistry).where(
                IdentifierRegistry.project_id.in_(
                    project_ids
                )
            )
        )

        project_result = session.execute(
            delete(Project).where(
                Project.strategy_name
                == cleaned_strategy_name
            )
        )

        session.commit()

    except Exception:
        session.rollback()
        raise

    return {
        "projects_deleted": _safe_rowcount(
            project_result.rowcount
        ),
        "identifiers_deleted": _safe_rowcount(
            identifier_result.rowcount
        ),
    }


def clear_all_table_data(
    session: Session,
) -> dict[str, int]:
    """
    Delete every identifier and project while keeping both tables.

    This is more destructive than ``delete_all_identifiers()`` because Project
    Tags are also removed. It should be restricted to administrative or
    development use.

    Returns
    -------
    dict[str, int]
        Number of deleted projects and identifier rows.
    """
    try:
        identifier_result = session.execute(
            delete(IdentifierRegistry)
        )

        project_result = session.execute(
            delete(Project)
        )

        session.commit()

    except Exception:
        session.rollback()
        raise

    return {
        "projects_deleted": _safe_rowcount(
            project_result.rowcount
        ),
        "identifiers_deleted": _safe_rowcount(
            identifier_result.rowcount
        ),
    }