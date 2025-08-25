
from contextlib import contextmanager
from sqlmodel import SQLModel, Session, create_engine

DATABASE_URL = "sqlite:///database.db"  # or your connection string
engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
