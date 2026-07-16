from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class Project(Base):
    __tablename__ = "projects"

    __table_args__ = (
        UniqueConstraint(
            "name",
            "strategy_name",
            name="uq_project_name_strategy",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

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
        passive_deletes =True,
    )

class IdentifierRegistry(Base):
    __tablename__ = "identifier_registry"

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "identifier_value",
            name="uq_project_identifier",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    project_id: Mapped[int] = mapped_column(
        ForeignKey(
            "projects.id",
            ondelete ="CASCADE",
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