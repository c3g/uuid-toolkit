import argparse

from db.database import engine
from db.schema_management import reset_all_tables


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Drop all application tables and recreate them "
            "from the current SQLAlchemy models."
        )
    )
    parser.add_argument(
        "--confirm-reset",
        action="store_true",
        help="Required confirmation for the destructive reset.",
    )

    args = parser.parse_args()

    if not args.confirm_reset:
        raise SystemExit(
            "Reset cancelled. Run again with --confirm-reset."
        )

    reset_all_tables(engine)
    print("All tables were dropped and recreated successfully.")


if __name__ == "__main__":
    main()