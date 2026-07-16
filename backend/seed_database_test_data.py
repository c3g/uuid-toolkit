"""
Seed robust CPHI and PCGL test data into the local PostgreSQL database.

Place this file in the backend root, where imports such as `db.database`
and `db.models` work, then run:

    python seed_database_test_data.py

The script is idempotent:
- missing projects are created
- missing project/identifier pairs are created
- existing rows are skipped

It also creates two CSV files for Swagger testing:
- cphi_database_scope_test.csv
- pcgl_database_scope_test.csv
"""

from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy import select

from db.database import SessionLocal
from db.models import IdentifierRegistry, Project


PROJECT_DEFINITIONS = [
    {
        "name": "C3G CPHI Test A",
        "strategy_name": "CPHI",
        "description": "CPHI project A for database conflict testing.",
    },
    {
        "name": "C3G CPHI Test B",
        "strategy_name": "CPHI",
        "description": "CPHI project B for database conflict testing.",
    },
    {
        "name": "C3G PCGL Test A",
        "strategy_name": "PCGL",
        "description": "PCGL project A for database conflict testing.",
    },
    {
        "name": "C3G PCGL Test B",
        "strategy_name": "PCGL",
        "description": "PCGL project B for database conflict testing.",
    },
    {
        "name": "Unassigned",
        "strategy_name": "PCGL",
        "description": "Default unassigned project for PCGL identifiers.",
    },
]


IDENTIFIER_DEFINITIONS = [
    # CPHI Test A
    ("C3G CPHI Test A", "CPHI", "NRGI-111111"),
    ("C3G CPHI Test A", "CPHI", "NRGI-222222"),
    ("C3G CPHI Test A", "CPHI", "NRGI-555555"),

    # CPHI Test B
    ("C3G CPHI Test B", "CPHI", "NRGI-333333"),
    ("C3G CPHI Test B", "CPHI", "NRGI-444444"),
    ("C3G CPHI Test B", "CPHI", "NRGI-555555"),

    # PCGL Test A
    ("C3G PCGL Test A", "PCGL", "NRGI-111111_EXP_0001"),
    ("C3G PCGL Test A", "PCGL", "NRGI-111111_LIB_0001"),
    ("C3G PCGL Test A", "PCGL", "NRGI-222222_SPE_0001"),
    ("C3G PCGL Test A", "PCGL", "NRGI-555555_EXP_0001"),

    # PCGL Test B
    ("C3G PCGL Test B", "PCGL", "NRGI-333333_EXP_0001"),
    ("C3G PCGL Test B", "PCGL", "NRGI-333333_RG_0001"),
    ("C3G PCGL Test B", "PCGL", "NRGI-444444_ANA_0001"),
    ("C3G PCGL Test B", "PCGL", "NRGI-555555_EXP_0001"),

    # Unassigned PCGL
    ("Unassigned", "PCGL", "NRGI-777777_WRK_0001"),
]


def get_or_create_project(
    session,
    *,
    name: str,
    strategy_name: str,
    description: str,
) -> tuple[Project, bool]:
    statement = (
        select(Project)
        .where(Project.name == name)
        .where(Project.strategy_name == strategy_name)
    )

    project = session.execute(statement).scalar_one_or_none()

    if project is not None:
        return project, False

    project = Project(
        name=name,
        strategy_name=strategy_name,
        description=description,
    )
    session.add(project)
    session.flush()

    return project, True


def add_identifier_if_missing(
    session,
    *,
    project: Project,
    identifier_value: str,
    strategy_name: str,
) -> bool:
    statement = (
        select(IdentifierRegistry)
        .where(IdentifierRegistry.project_id == project.id)
        .where(
            IdentifierRegistry.identifier_value
            == identifier_value
        )
    )

    existing_identifier = (
        session.execute(statement).scalar_one_or_none()
    )

    if existing_identifier is not None:
        return False

    session.add(
        IdentifierRegistry(
            project_id=project.id,
            identifier_value=identifier_value,
            strategy_name=strategy_name,
        )
    )

    return True


def write_csv(
    filename: str,
    rows: list[dict[str, str]],
) -> None:
    path = Path(filename)

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "identifier",
                "expected_when_test_a_selected",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Created test file: {path.resolve()}")


def main() -> None:
    created_projects = 0
    created_identifiers = 0

    with SessionLocal() as session:
        projects_by_key: dict[tuple[str, str], Project] = {}

        for definition in PROJECT_DEFINITIONS:
            project, was_created = get_or_create_project(
                session,
                name=definition["name"],
                strategy_name=definition["strategy_name"],
                description=definition["description"],
            )

            projects_by_key[
                (
                    definition["name"],
                    definition["strategy_name"],
                )
            ] = project

            if was_created:
                created_projects += 1

        for (
            project_name,
            strategy_name,
            identifier_value,
        ) in IDENTIFIER_DEFINITIONS:
            project = projects_by_key[
                (project_name, strategy_name)
            ]

            was_created = add_identifier_if_missing(
                session,
                project=project,
                identifier_value=identifier_value,
                strategy_name=strategy_name,
            )

            if was_created:
                created_identifiers += 1

        session.commit()

        for project in projects_by_key.values():
            session.refresh(project)

        print("\nSeed complete.")
        print(f"Projects created: {created_projects}")
        print(f"Identifiers created: {created_identifiers}")

        print("\nTest projects:")
        for key, project in sorted(
            projects_by_key.items(),
            key=lambda item: item[1].id,
        ):
            print(
                f"  ID {project.id}: "
                f"{project.name} [{project.strategy_name}]"
            )

        cphi_project_a = projects_by_key[
            ("C3G CPHI Test A", "CPHI")
        ]
        pcgl_project_a = projects_by_key[
            ("C3G PCGL Test A", "PCGL")
        ]

        print("\nSuggested selected-project tests:")
        print(
            f"  CPHI project_id: {cphi_project_a.id}"
        )
        print(
            f"  PCGL project_id: {pcgl_project_a.id}"
        )

    write_csv(
        "cphi_database_scope_test.csv",
        [
            {
                "identifier": "NRGI-111111",
                "expected_when_test_a_selected": "hard conflict",
            },
            {
                "identifier": "NRGI-333333",
                "expected_when_test_a_selected": "soft warning",
            },
            {
                "identifier": "NRGI-555555",
                "expected_when_test_a_selected": (
                    "hard conflict; also exists in Test B"
                ),
            },
            {
                "identifier": "NRGI-999999",
                "expected_when_test_a_selected": "no DB conflict",
            },
        ],
    )

    write_csv(
        "pcgl_database_scope_test.csv",
        [
            {
                "identifier": "NRGI-111111_EXP_0001",
                "expected_when_test_a_selected": "hard conflict",
            },
            {
                "identifier": "NRGI-333333_EXP_0001",
                "expected_when_test_a_selected": "soft warning",
            },
            {
                "identifier": "NRGI-555555_EXP_0001",
                "expected_when_test_a_selected": (
                    "hard conflict; also exists in Test B"
                ),
            },
            {
                "identifier": "NRGI-999999_EXP_0001",
                "expected_when_test_a_selected": "no DB conflict",
            },
        ],
    )

    print("\nSwagger test settings:")
    print("  id_name: identifier")
    print("  CPHI strategy_name: CPHI")
    print("  PCGL strategy_name: PCGL")
    print(
        "  For PCGL, use the validation config required by "
        "your strategy for the EXP variant."
    )


if __name__ == "__main__":
    main()