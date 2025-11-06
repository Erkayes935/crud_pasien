import os
"""
Module: backend.database

Configures the SQLAlchemy Engine, `SessionLocal` factory, and declarative
`Base` used by ORM models. The connection URL is read from the
`DATABASE_URL` environment variable (use `.env` locally). Keep this module
lightweight to avoid side-effects; importing it will create the engine which
may attempt to connect to the database depending on driver behavior.
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

# Load .env for local development (no-op if no .env present)
load_dotenv()

# Read DB URL from environment; fallback to a sensible default for local dev
DATABASE_URL = os.getenv("DATABASE_URL")

# Create engine and session factory
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # cek koneksi otomatis
    pool_recycle=1800,    # reset koneksi idle >30 menit
    poolclass=NullPool,   # hindari idle socket leak di Docker
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# ---------------------------
# DB dependency
# ---------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()