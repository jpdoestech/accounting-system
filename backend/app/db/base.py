"""
Database engine/session setup.

Uses SQLite for development (spec Section 7) and works identically
against PostgreSQL in production by swapping DATABASE_URL only -- no
code changes required. Monetary columns must always use SQLAlchemy
Numeric (DECIMAL), never Float -- see app/utils/money.py.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
