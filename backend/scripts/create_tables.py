from db.database import engine
from db.schema_management import create_all_tables


def main() -> None:
    create_all_tables(engine)
    print("Database tables created.")


if __name__ == "__main__":
    main()