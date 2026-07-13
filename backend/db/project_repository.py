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
    project = Project(
        name= name,
        strategy_name = strategy_name,
        description = description,
    )

    session.add(project)
    session.commit()
    session.refresh(project)

    return project

def list_projects(session: Session) -> list[Project]:
    statement = select(Project).order_by(Project.id)

    result = session.execute(statement)

    return list(result.scalars().all())

def get_project_by_id(
        session:Session,
        *,
        project_id: int,
    )-> Project|None:
    statement = select(Project).where(Project.id == project_id)

    result = session.execute(statement)

    return result.scalar_one_or_none()

def get_project_by_name(
        session: Session,
        *,
        name:str,
    ) -> Project|None:
    statement = select(Project).where(Project.name == name)

    result = session.execute(statement)

    return result.scalar_one_or_none()

def get_or_create_unassigned_project(
        session: Session,
        *,
        strategy_name:str,
) -> Project:
    
    statement = (
        select(Project)
        .where(Project.name == "Unassigned")
        .where(Project.strategy_name== strategy_name)
    )

    existing_projects = session.execute(statement).scalar_one_or_none()

    if existing_projects is not None:
        return existing_projects
    
    project = Project(
        name = "Unassigned",
        strategy_name = strategy_name,
        description = f"Default unassigned project name for {strategy_name} identifiers."
    )

    session.add(project)
    session.commit()
    session.refresh(project)

    return project

