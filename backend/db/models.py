"""
SQLAlchemy models for projects and stored identifiers.

This file defines the database tables used by the identifier registry:

- ``Project`` groups identifiers under one strategy.
- ``IdentifierRegistry`` stores the identifier values saved to each project.

How this file connects to the project
-------------------------------------
- ``database.py`` provides the SQLAlchemy engine and sessions.
- ``schema_management.py`` creates or drops the tables defined here.
- ``project_repository.py`` reads and creates ``Project`` records.
- ``identifier_repository.py`` reads, compares, and saves
  ``IdentifierRegistry`` records.
- ``database_management.py`` deletes projects and identifiers.
- ``comparison.py`` checks pipeline results against stored identifiers.
- API routes return these records to ``ToolkitPage.jsx`` and
  ``DatabaseManagementPage.jsx``.

Adding a new strategy
---------------------
This file normally does not need to change when a new strategy is added.
Projects and identifiers store ``strategy_name`` as a regular string, so the
same tables can support any strategy registered by the application.

A model change is only needed if the new strategy requires additional data to
be stored. In that case, update this file and create a database migration before
deploying the change.
"""

from sqlalchemy import (
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    """
    Base class used by every SQLAlchemy model in the project.

    ``schema_management.py`` uses ``Base.metadata`` to create and drop the
    registered database tables.
    """

    pass


class Project(Base):
    """
    Store one Project Tag for an identifier strategy.

    Project names only need to be unique within the same strategy. For example,
    a project named ``"Unassigned"`` can exist once for CPHI and once for PCGL.

    Deleting a project also deletes its related identifier rows through the
    relationship and foreign-key cascade rules.
    """

    __tablename__ = "projects"

    __table_args__ = (
        UniqueConstraint(
            "name",
            "strategy_name",
            name="uq_project_name_strategy",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    strategy_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    identifiers: Mapped[list["IdentifierRegistry"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class IdentifierRegistry(Base):
    """
    Store one identifier under a project.

    The same identifier value cannot appear more than once inside the same
    project. It may appear in another project, where it is treated as a soft
    warning by the database comparison workflow.

    ``strategy_name`` is stored on the identifier row as well as the project so
    strategy-wide conflict queries can filter identifier records directly.
    """

    __tablename__ = "identifier_registry"

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "identifier_value",
            name="uq_project_identifier",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    project_id: Mapped[int] = mapped_column(
        ForeignKey(
            "projects.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    identifier_value: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    strategy_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    project: Mapped["Project"] = relationship(
        back_populates="identifiers",
    )