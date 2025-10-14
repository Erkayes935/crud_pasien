"""
Module: database_connection

Database connection untuk core_engine agar bisa akses rules_master table.
Menggunakan konfigurasi yang sama dengan web container.
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Load .env for environment variables
load_dotenv()

# Read DB URL from environment (sama dengan web)
DATABASE_URL = os.getenv("DATABASE_URL")

# Create engine and session factory
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# ---------------------------
# DB dependency untuk FastAPI
# ---------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------
# Get direct session (untuk rules_loader.py)
# ---------------------------
def get_db_session():
    """Get database session untuk digunakan langsung di rules_loader"""
    return SessionLocal()