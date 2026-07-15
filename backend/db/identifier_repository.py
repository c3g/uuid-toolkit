from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from db.models import IdentifierRegistry, Project

def list_identifiers(
        session:Session,
)-> list[IdentifierRegistry]:
    statement = (
        select(IdentifierRegistry)
        .order_by(IdentifierRegistry.id)
        )

    result = session.execute(statement)

    return list(result.scalars().all())

def list_identifiers_by_project(
        session:Session,
        *,
        project_id: int,
)-> list[IdentifierRegistry]:
    statement = (
        select(IdentifierRegistry)
        .where(IdentifierRegistry.project_id == project_id)
        .order_by(IdentifierRegistry.id)
    )
    result = session.execute(statement)

    return list(result.scalars().all())

def list_identifiers_by_strategy(
        session:Session,
        *,
        strategy_name: str,
) -> list[IdentifierRegistry]:
    statement = (
        select(IdentifierRegistry)
        .where(IdentifierRegistry.strategy_name == strategy_name)
        .order_by(IdentifierRegistry.id)
    )
    result = session.execute(statement)

    return list(result.scalars().all())


def find_project_conflicts(
    session: Session,
    *,
    project_id:int,
    identifiers: set[str]
)-> set[str]:
    if not identifiers:
        return set()
    statement = (
        select(IdentifierRegistry.identifier_value)
        .where(IdentifierRegistry.project_id == project_id)
        .where(IdentifierRegistry.identifier_value.in_(identifiers))
    )
    result = session.execute(statement)

    return set(result.scalars().all())

def find_strategy_conflicts(
        session:Session,
        *,
        strategy_name:str,
        identifiers:set[str],
) -> set[str]:
    """
    Find identifiers that already exist under the given strategy regardless of project.
    Used when the user doesn't select a project tag.
    """

    if not identifiers:
        return set()
    
    statement = (
        select(IdentifierRegistry.identifier_value)
        .where(IdentifierRegistry.strategy_name== strategy_name)
        .where(IdentifierRegistry.identifier_value.in_(identifiers))
    )

    result = session.execute(statement)

    return set(result.scalars().all())

def save_identifiers_to_project(
        session: Session,
        *,
        project_id: int,
        strategy_name: str,
        identifiers: set[str],
)-> list[IdentifierRegistry]:
    """
    Save clean identifiers to a project.

    The database prevents duplicate identifiers within the same project.
    """

    saved_identifiers = [
        IdentifierRegistry(
            project_id = project_id,
            identifier_value = identifier,
            strategy_name = strategy_name,
        )
        for identifier in identifiers
    ]

    try: 
        session.add_all(saved_identifiers)
        session.commit()

    except IntegrityError as error:
        session.rollback()
        raise ValueError("One or more identifiers already exist in this project.") from error
    
    for saved_identifier in saved_identifiers:
        session.refresh(saved_identifier)
    
    return saved_identifiers

def find_other_project_matches(
        session: Session,
        *,
        project_id:int,
        strategy_name:str,
        identifiers:set[str],
)->dict[str,list[str]]:
    """
    Find identifiers that exist in other projects under the same strategy.
    """

    if not identifiers:
        return {}
    
    statement = (
        select(
            IdentifierRegistry.identifier_value,
            Project.name,
        )
        .join(Project, IdentifierRegistry.project_id == Project.id)
        .where(IdentifierRegistry.project_id != project_id)
        .where(IdentifierRegistry.strategy_name == strategy_name)
        .where(IdentifierRegistry.identifier_value.in_(identifiers))
    )

    rows = session.execute(statement).all()

    matches: dict[str,list[str]]= {}

    for identifier_value, project_name in rows:
        matches.setdefault(identifier_value,[]).append(project_name)
    
    return matches