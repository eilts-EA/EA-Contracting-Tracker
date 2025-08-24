
from contextlib import contextmanager
from sqlmodel import SQLModel, create_engine, Session
import os

DB_URL = os.getenv("DATA_GUI_DB_URL", "sqlite:///data.db")
connect_args = {"check_same_thread": False} if DB_URL.startswith("sqlite") else {}

engine = create_engine(DB_URL, echo=False, pool_pre_ping=True, connect_args=connect_args)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

@contextmanager
def get_session():
    with Session(engine) as session:
        yield session
