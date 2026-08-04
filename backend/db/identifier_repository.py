"""
Repository functions for stored identifiers.

This file contains the database queries used to list, compare, and save
``IdentifierRegistry`` records. It keeps SQLAlchemy query logic separate from
the API routes and the higher-level database comparison workflow.

How this file connects to the project
-------------------------------------
- ``api/identifier_database.py`` uses these functions to list and save stored
  identifiers.
- ``db/comparison.py`` uses the conflict queries before and after the validation
  and generation pipelines run.
- ``db/models.py`` defines ``IdentifierRegistry`` and ``Project``.
- ``db/database.py`` provides the SQLAlchemy session.
- ``DatabaseManagementPage.jsx`` displays the records returned by the API.
- ``ToolkitPage.jsx`` saves clean identifiers after validation or generation.

Database comparison rules
-------------------------
- ``find_project_conflicts()`` checks for hard conflicts inside one selected
  project.
- ``find_strategy_conflicts()`` checks for hard conflicts across a complete
  strategy when no project is selected.
- ``find_other_project_matches()`` finds soft-warning matches in other projects
  under the same strategy.

Adding a new strategy
---------------------
This file normally does not need to change when a strategy is added because
identifiers are queried using their stored ``strategy_name``.

A change is only needed when a new strategy stores identifiers differently or
requires a different conflict scope. Normal strategy setup belongs in the
strategy class, ``registry.py``, ``api/utils.py``, frontend config files, and
tests.
"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.models import IdentifierRegistry, Project


def list_identifiers(
    session: Session,
) -> list[IdentifierRegistry]:
    """
    Return every stored identifier ordered by database row ID.

    Parameters
    ----------
    session:
        Active SQLAlchemy session.

    Returns
    -------
    list[IdentifierRegistry]
        All identifier records in insertion order.
    """
    statement = (
        select(IdentifierRegistry)
        .order_by(IdentifierRegistry.id)
    )

    result = session.execute(statement)

    return list(result.scalars().all())


def list_identifiers_by_project(
    session: Session,
    *,
    project_id: int,
) -> list[IdentifierRegistry]:
    """
    Return identifiers belonging to one project.

    Parameters
    ----------
    session:
        Active SQLAlchemy session.

    project_id:
        Database ID of the selected project.

    Returns
    -------
    list[IdentifierRegistry]
        Matching identifier records ordered by row ID.
    """
    statement = (
        select(IdentifierRegistry)
        .where(
            IdentifierRegistry.project_id
            == project_id
        )
        .order_by(IdentifierRegistry.id)
    )

    result = session.execute(statement)

    return list(result.scalars().all())


def list_identifiers_by_strategy(
    session: Session,
    *,
    strategy_name: str,
) -> list[IdentifierRegistry]:
    """
    Return identifiers stored under one strategy.

    The caller should pass the normalized strategy name used by the database,
    such as ``"UUID"``, ``"CPHI"``, ``"PCGL"``, or ``"CUSTOM"``.

    Parameters
    ----------
    session:
        Active SQLAlchemy session.

    strategy_name:
        Strategy used to filter the identifier records.

    Returns
    -------
    list[IdentifierRegistry]
        Matching identifier records ordered by row ID.
    """
    statement = (
        select(IdentifierRegistry)
        .where(
            IdentifierRegistry.strategy_name
            == strategy_name
        )
        .order_by(IdentifierRegistry.id)
    )

    result = session.execute(statement)

    return list(result.scalars().all())


def find_project_conflicts(
    session: Session,
    *,
    project_id: int,
    identifiers: set[str],
) -> set[str]:
    """
    Find submitted identifiers that already exist in one project.

    This query is used for hard-conflict checks when the user selects a Project
    Tag.

    Parameters
    ----------
    session:
        Active SQLAlchemy session.

    project_id:
        Project used as the hard-conflict scope.

    identifiers:
        Identifier values to compare with the database.

    Returns
    -------
    set[str]
        Submitted values already stored inside the project.
    """
    if not identifiers:
        return set()

    statement = (
        select(
            IdentifierRegistry.identifier_value
        )
        .where(
            IdentifierRegistry.project_id
            == project_id
        )
        .where(
            IdentifierRegistry.identifier_value.in_(
                identifiers
            )
        )
    )

    result = session.execute(statement)

    return set(result.scalars().all())


def find_strategy_conflicts(
    session: Session,
    *,
    strategy_name: str,
    identifiers: set[str],
) -> set[str]:
    """
    Find submitted identifiers that already exist under one strategy.

    This query is used for hard-conflict checks when the user does not select a
    Project Tag.

    Parameters
    ----------
    session:
        Active SQLAlchemy session.

    strategy_name:
        Strategy used as the hard-conflict scope.

    identifiers:
        Identifier values to compare with the database.

    Returns
    -------
    set[str]
        Submitted values already stored under the strategy.
    """
    if not identifiers:
        return set()

    statement = (
        select(
            IdentifierRegistry.identifier_value
        )
        .where(
            IdentifierRegistry.strategy_name
            == strategy_name
        )
        .where(
            IdentifierRegistry.identifier_value.in_(
                identifiers
            )
        )
    )

    result = session.execute(statement)

    return set(result.scalars().all())


def save_identifiers_to_project(
    session: Session,
    *,
    project_id: int,
    strategy_name: str,
    identifiers: set[str],
) -> list[IdentifierRegistry]:
    """
    Save clean identifiers under one project.

    The database unique constraint prevents the same identifier from appearing
    more than once inside the same project.

    Parameters
    ----------
    session:
        Active SQLAlchemy session.

    project_id:
        Destination project.

    strategy_name:
        Strategy assigned to the saved records.

    identifiers:
        Clean and unique identifier values to save.

    Returns
    -------
    list[IdentifierRegistry]
        Newly created and refreshed database records.

    Raises
    ------
    ValueError
        Raised when one or more identifiers conflict with records already
        stored in the destination project.

    Notes
    -----
    ``api/identifier_database.py`` checks for existing project conflicts before
    calling this function. The database constraint still acts as the final
    safeguard in case another request saves the same identifier at the same
    time.
    """
    saved_identifiers = [
        IdentifierRegistry(
            project_id=project_id,
            identifier_value=identifier,
            strategy_name=strategy_name,
        )
        for identifier in identifiers
    ]

    try:
        session.add_all(saved_identifiers)
        session.commit()

    except IntegrityError as error:
        session.rollback()

        raise ValueError(
            "One or more identifiers already exist "
            "in this project."
        ) from error

    for saved_identifier in saved_identifiers:
        session.refresh(saved_identifier)

    return saved_identifiers


def find_other_project_matches(
    session: Session,
    *,
    project_id: int,
    strategy_name: str,
    identifiers: set[str],
) -> dict[str, list[str]]:
    """
    Find matching identifiers in other projects under the same strategy.

    This query supports soft warnings. The selected project is excluded because
    matches inside that project are handled separately as hard conflicts.

    Parameters
    ----------
    session:
        Active SQLAlchemy session.

    project_id:
        Selected project that should be excluded from the search.

    strategy_name:
        Strategy used to limit the search.

    identifiers:
        Identifier values to compare with other projects.

    Returns
    -------
    dict[str, list[str]]
        Mapping from each matching identifier to the names of the other
        projects containing it.

        Example:

        {
            "NRGI-123456": [
                "Project A",
                "Project B",
            ]
        }
    """
    if not identifiers:
        return {}

    statement = (
        select(
            IdentifierRegistry.identifier_value,
            Project.name,
        )
        .join(
            Project,
            IdentifierRegistry.project_id
            == Project.id,
        )
        .where(
            IdentifierRegistry.project_id
            != project_id
        )
        .where(
            IdentifierRegistry.strategy_name
            == strategy_name
        )
        .where(
            IdentifierRegistry.identifier_value.in_(
                identifiers
            )
        )
    )

    rows = session.execute(statement).all()

    matches: dict[str, list[str]] = {}

    for identifier_value, project_name in rows:
        matches.setdefault(
            identifier_value,
            [],
        ).append(project_name)

    return matches