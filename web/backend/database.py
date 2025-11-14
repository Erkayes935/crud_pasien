import os
"""
Module: backend.database

Configures the SQLAlchemy Engine, `SessionLocal` factory, and declarative
`Base` used by ORM models. The connection URL is read from the
`DATABASE_URL` environment variable (use `.env` locally). Keep this module
lightweight to avoid side-effects; importing it will create the engine which
may attempt to connect to the database depending on driver behavior.

DUAL DATABASE SETUP:
- ai_claim_db (port 5434): Web application + Claims data
- datahub_db (port 5433): Data Hub standardization & ingestion
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

# Load .env for local development (no-op if no .env present)
load_dotenv()

# ============================================================
# AI CLAIM DATABASE (Web + Claims)
# ============================================================
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
# DB dependency for AI Claim
# ---------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================
# DATA HUB DATABASE (Standardization & Ingestion)
# ============================================================
DATABASE_URL_DATAHUB = os.getenv(
    "DATABASE_URL_DATAHUB",
    "postgresql://datahub_user:pass@103.179.56.158:5433/datahub_db"
)

# Create datahub engine and session factory
engine_datahub = create_engine(
    DATABASE_URL_DATAHUB,
    pool_pre_ping=True,
    pool_recycle=1800,
    poolclass=NullPool,
)
SessionLocalDataHub = sessionmaker(bind=engine_datahub, autoflush=False, autocommit=False)
BaseDataHub = declarative_base()

# ---------------------------
# DB dependency for Data Hub
# ---------------------------
def get_datahub_session():
    db = SessionLocalDataHub()
    try:
        yield db
    finally:
        db.close()