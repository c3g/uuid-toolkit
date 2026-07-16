from sqlalchemy.engine import Engine

from db.models import Base


def drop_all_tables(engine: Engine) -> None:
    """
    Permanently drop every table registered under Base metadata.
    """
    Base.metadata.drop_all(bind=engine)


def create_all_tables(engine: Engine) -> None:
    """
    Create all missing tables from the current SQLAlchemy models.
    """
    Base.metadata.create_all(bind=engine)


def reset_all_tables(engine: Engine) -> None:
    """
    Drop every table and recreate them from the current models.

    This permanently deletes all stored data.
    """
    drop_all_tables(engine)
    create_all_tables(engine)