"""
Module: backend.models

Defines the SQLAlchemy ORM models used by the application:
- Patient: stores patient personal and visit information.
- User: stores application users linked to Auth0 via `auth0_sub` and a role.

Fields use SQLAlchemy column types (String, Date, Text). Dates are stored as
`Date` objects; when creating patients from form data ensure strings are
parsed into date objects where necessary.
"""

from sqlalchemy import Column, Integer, String, Date, Text
from .database import Base

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    nama = Column(String(100), nullable=False)
    tanggal_lahir = Column(Date)
    tanggal_kunjungan = Column(Date, nullable=False)
    diagnosis = Column(Text)
    tindakan = Column(Text)
    dokter = Column(String(100))

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    auth0_sub = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    role = Column(String, default="doctor", nullable=False)