from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from db.models import IdentifierRegistry

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