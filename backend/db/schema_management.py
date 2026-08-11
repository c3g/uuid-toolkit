"""
Helpers for creating, dropping, and resetting database tables.

This file uses the SQLAlchemy models registered under ``Base.metadata``.

How this file connects to the project
-------------------------------------
- ``models.py`` defines the tables stored under ``Base.metadata``.
- ``database.py`` provides the SQLAlchemy engine passed into these functions.
- Setup scripts may call ``create_all_tables()`` when preparing a new database.
- Development or maintenance scripts may call ``drop_all_tables()`` or
  ``reset_all_tables()``.

Adding a new strategy
---------------------
This file normally does not need to change when a new strategy is added.

When a strategy uses the existing ``Project`` and ``IdentifierRegistry``
tables, only the strategy registry, API config validation, frontend controls,
and tests need to be updated.

When a strategy requires a new table or column:

1. Update ``models.py``.
2. Create a database migration for existing environments.
3. Update the related repository and API files.
4. Add tests for the new database behavior.

Do not use ``reset_all_tables()`` to update a production database because it
deletes all stored data.
"""

from sqlalchemy.engine import Engine

from db.models import Base


def drop_all_tables(
    engine: Engine,
) -> None:
    """
    Permanently drop every table registered under ``Base.metadata``.

    Parameters
    ----------
    engine:
        SQLAlchemy engine connected to the target database.

    Notes
    -----
    This deletes the tables and all data stored inside them. It should only be
    used for development, testing, or controlled maintenance.
    """
    Base.metadata.drop_all(bind=engine)


def create_all_tables(
    engine: Engine,
) -> None:
    """
    Create any missing tables registered under ``Base.metadata``.

    Parameters
    ----------
    engine:
        SQLAlchemy engine connected to the target database.

    Notes
    -----
    This creates missing tables but does not safely modify existing table
    structures. Use database migrations when changing columns, constraints, or
    existing production tables.
    """
    Base.metadata.create_all(bind=engine)


def reset_all_tables(
    engine: Engine,
) -> None:
    """
    Drop and recreate every table registered under ``Base.metadata``.

    Parameters
    ----------
    engine:
        SQLAlchemy engine connected to the target database.

    Notes
    -----
    This permanently deletes all projects and identifiers before recreating
    the tables. It should only be used in development or testing.
    """
    drop_all_tables(engine)
    create_all_tables(engine)