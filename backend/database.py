import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Load .env for local development (no-op if no .env present)
load_dotenv()

# Read DB URL from environment; fallback to a sensible default for local dev
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:root@localhost:5432/patients")

# Create engine and session factory
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()
