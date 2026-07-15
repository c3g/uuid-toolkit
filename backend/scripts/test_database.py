from db.database import SessionLocal
from db.identifier_repository import (
    find_project_conflicts,
    find_strategy_conflicts,
    save_identifiers_to_project,
)
from db.project_repository import (
    create_project,
    get_or_create_unassigned_project,
    get_project_by_name,
    list_projects,
)
from db.identifier_repository import (
    find_project_conflicts,
    find_strategy_conflicts,
    save_identifiers_to_project,
    list_identifiers,
    list_identifiers_by_project,
    list_identifiers_by_strategy,
)


def main() -> None:
    session = SessionLocal()

    try:
        project_name = "Brain Tumor Study CPHI"

        project = get_project_by_name(
            session,
            name=project_name,
        )

        if project is None:
            project = create_project(
                session,
                name=project_name,
                strategy_name="CPHI",
                description="Testing CPHI project IDs.",
            )

        print("Project:", project.id, project.name, project.strategy_name)

        existing_conflicts = find_project_conflicts(
            session,
            project_id=project.id,
            identifiers={"NRGI-123456", "NRGI-789012"},
        )

        identifiers_to_save = [
            identifier
            for identifier in ["NRGI-123456", "NRGI-789012"]
            if identifier not in existing_conflicts
        ]

        if identifiers_to_save:
            saved = save_identifiers_to_project(
                session,
                project_id=project.id,
                strategy_name="CPHI",
                identifiers=identifiers_to_save,
            )

            print("Saved count:", len(saved))
        else:
            print("No new identifiers to save.")

        project_conflicts = find_project_conflicts(
            session,
            project_id=project.id,
            identifiers={"NRGI-123456", "NRGI-000000"},
        )

        print("Project conflicts:", project_conflicts)

        strategy_conflicts = find_strategy_conflicts(
            session,
            strategy_name="CPHI",
            identifiers={"NRGI-123456", "NRGI-000000"},
        )

        print("Strategy conflicts:", strategy_conflicts)

        unassigned_project = get_or_create_unassigned_project(
            session,
            strategy_name="CPHI",
        )

        print(
            "Unassigned project:",
            unassigned_project.id,
            unassigned_project.name,
            unassigned_project.strategy_name,
        )

        print("All projects:")

        for item in list_projects(session):
            print(item.id, item.name, item.strategy_name)
        
        print("All identifier records:")

        for item in list_identifiers(session):
            print(
                item.id,
                item.project_id,
                item.identifier_value,
                item.strategy_name,
            )

        print("Identifiers in this project:")

        for item in list_identifiers_by_project(
            session,
            project_id=project.id,
        ):
            print(
                item.id,
                item.project_id,
                item.identifier_value,
                item.strategy_name,
            )

        print("CPHI identifiers:")

        for item in list_identifiers_by_strategy(
            session,
            strategy_name="CPHI",
        ):
            print(
                item.id,
                item.project_id,
                item.identifier_value,
                item.strategy_name,
            )

    finally:
        session.close()


if __name__ == "__main__":
    main()