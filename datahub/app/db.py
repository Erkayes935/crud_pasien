from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import ArgumentError
from .models.core import Base
import os

DATABASE_URL = os.getenv("DATABASE_URL")

_SKIP_CREATE_ALL = os.getenv("SKIP_CREATE_ALL", "0") in ("1", "true", "True")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set. Set it to a valid SQLAlchemy URL.")

try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
except ArgumentError as e:
    raise RuntimeError(f"Invalid DATABASE_URL: {e}") from e

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    if _SKIP_CREATE_ALL:
        return
    Base.metadata.create_all(bind=engine)

def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
