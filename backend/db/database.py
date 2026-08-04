"""
Database connection and SQLAlchemy session setup.

This file loads the database URL, creates the SQLAlchemy engine, and provides
the session dependency used by FastAPI routes.

The request flow is:

    FastAPI route
        -> get_db_session()
        -> SQLAlchemy session
        -> repository or database service
        -> PostgreSQL

How this file connects to the project
-------------------------------------
- API route files use ``Depends(get_db_session)`` to receive a database session.
- Repository files use the session to run ``select()``, ``delete()``, and
  insert operations.
- ``schema_management.py`` uses ``engine`` when creating, dropping, or resetting
  tables.
- ``models.py`` defines the tables that SQLAlchemy maps to the database.
- The database URL is loaded from the backend ``.env`` file.

Adding a new strategy
---------------------
This file normally does not change when a new identifier strategy is added.
Strategies share the same database connection and session setup.

A new strategy may require model or migration changes when it needs additional
stored fields, but those changes belong in ``models.py`` and the database
migration layer rather than here.

Production notes
----------------
- ``DATABASE_URL`` should come from a production environment variable and
  should never be committed to Git.
- The production database user should only have the permissions required by
  the application.
- Connection-pool settings can be added to ``create_engine()`` later based on
  the production environment.
"""

import os
from collections.abc import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


# Load environment variables from the backend .env file during local
# development. Production environments can provide the same values directly.
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL is None:
    raise RuntimeError("DATABASE_URL is not set.")


# The engine manages connections between SQLAlchemy and PostgreSQL.
engine = create_engine(DATABASE_URL)


# SessionLocal creates a new database session whenever the application needs
# one. The session is not opened until SessionLocal() is called.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def get_db_session() -> Generator[Session, None, None]:
    """
    Provide one SQLAlchemy session for a FastAPI request.

    The session is created when the route begins and is always closed after the
    request finishes, including when an exception occurs.

    Yields
    ------
    Session
        SQLAlchemy session used by the route and repository functions.

    Notes
    -----
    This function does not commit or roll back automatically. Repository and
    database service functions are responsible for committing successful
    changes and rolling back failed transactions.

    FastAPI usage example:

        session: Session = Depends(get_db_session)
    """
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()