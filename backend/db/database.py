import os
from collections.abc import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL is None:
    raise RuntimeError("DATABASE_URL is not set.")

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    bind = engine,
    autoflush = False,
    autocommit = False,
)

def get_db_session() -> Generator[Session,None,None]:
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()