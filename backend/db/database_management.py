from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.exec import IntegrityError
from sqlalchemy.orm import Session

from db.models import IdentifierRegistry,Project

def _safe_rowcount(rowcount: int | None) -> int:
    if rowcount is None or rowcount<0:
        return 0
    return rowcount

def create_project(
        session:Session,
        *,
        name: str,
        strategy_name: str,
        description: str | None = None,
)-> Project:
    """
    Create a project.

    Project names only need to be unique within the same strategy.
    For example, "Unassigned" may exist once for CPHI and once for PCGL.
    """

    cleaned_name = name.strip()
    cleaned_strategy_name = strategy_name.strip()

    if not cleaned_name:
        raise ValueError("Project name can not be empty.")
    
    if not cleaned_strategy_name:
        raise ValueError("Strategy name can not be empty")
    
    existing_statement = (
        select(Project)
        .where(Project.name == cleaned_name)
        .where(Project.strategy_name== cleaned_strategy_name)
    )

    existing_project = (session.execute(existing_statement).scalar_one_or_none())

    if existing_project is not None:
        raise ValueError(
            f"Project '{cleaned_name}' already exists under strategy '{cleaned_strategy_name}'."
        )
    
    project = Project(
        name = cleaned_name,
        strategy_name = cleaned_strategy_name,
        description = description.strip() if description else None,
    )

    try:
        session.add(project)
        session.commit()
        session.refresh(project)
    except IntegrityError as error:
        session.rollback()
        raise ValueError(
            "The project could not be created because it conflicts with an existing project"
        ) from error
    
    return project

def delete_identifier_by_id(
        session: Session,
        *,
        identifier_id: int,
)-> bool:
    """
    Delete an identifier-registry row by its database row ID.
    
    Returns true when a row as deleted and false when no row existed
    """

    try:
        result = session.execute(
            delete(IdentifierRegistry)
            .where(IdentifierRegistry.id == identifier_id)
        )
        session.commit()
    except Exception:
        session.rollback()
        raise

    return _safe_rowcount(result.rowcount) >0

def delete_identifiers_by_project(
        session: Session,
        *,
        project_id: int,
)-> int:
    """
    Delete every identifier that belongs to a certain project

    The project is kept and only the identifiers are removed
    """
    try:
        result = session.execute(
            delete(IdentifierRegistry)
            .where(IdentifierRegistry.project_id == project_id)
        )
        session.commit()
    except Exception:
        session.rollback()
        raise

    return _safe_rowcount(result.rowcount)

def delete_identifiers_by_strategy(
        session: Session,
        *,
        strategy_name:str,
)-> int:
    """
    Delete identifiers stored in one strategy.

    The strategy is kept and the projects still remain but without identifiers.
    """

    cleaned_strategy_name = strategy_name.strip()

    try:
        result = session.execute(
            delete(IdentifierRegistry)
            .where(IdentifierRegistry.strategy_name == cleaned_strategy_name)
        )
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
    Delete one project and all identifier rows belonging to it.

    Both deletions happen in the same transaction.
    """
    project = session.get(Project, project_id)

    if project is None:
        return {
            "project_deleted": False,
            "identifiers_deleted": 0,
        }

    try:
        identifier_result = session.execute(
            delete(IdentifierRegistry)
            .where(IdentifierRegistry.project_id == project_id)
        )

        project_result = session.execute(
            delete(Project)
            .where(Project.id == project_id)
        )

        session.commit()
    except Exception:
        session.rollback()
        raise

    return {
        "project_deleted": _safe_rowcount(
            project_result.rowcount
        ) > 0,
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
    Delete every project under one strategy and all of their identifiers.
    """
    cleaned_strategy_name = strategy_name.strip().upper()

    project_ids_statement = (
        select(Project.id)
        .where(Project.strategy_name == cleaned_strategy_name)
    )

    project_ids = set(
        session.execute(project_ids_statement).scalars().all()
    )

    if not project_ids:
        return {
            "projects_deleted": 0,
            "identifiers_deleted": 0,
        }

    try:
        identifier_result = session.execute(
            delete(IdentifierRegistry)
            .where(
                IdentifierRegistry.project_id.in_(project_ids)
            )
        )

        project_result = session.execute(
            delete(Project)
            .where(
                Project.strategy_name == cleaned_strategy_name
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
    Delete every identifier and project row while keeping both tables.

    This is destructive and should be restricted to development or admins.
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