from db.database import engine
from db.models import Base

def main() -> None:
    Base.metadata.create_all(bind=engine)
    print("Database tables crreated.")

if __name__ == "__main__":
    main()