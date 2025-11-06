from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, DateTime, text
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from .base import Base, HousekeepingMixin


# =========================================
# USER
# =========================================
class User(Base, HousekeepingMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    auth0_sub = Column(String, unique=True, index=True, nullable=True)   # Auth0 user_id
    email = Column(String, unique=True, index=True, nullable=True)
    name = Column(String, nullable=True)
    jabatan = Column(String, nullable=True)
    sip_number = Column(String, nullable=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True)

    # legacy single-role
    role = Column(String(50), nullable=True, default="doctor")

    # new multi-role system
    roles = relationship(
        "Role",
        secondary="user_roles",
        back_populates="users",
        overlaps="user_roles"
    )
    user_roles = relationship(
        "UserRole",
        back_populates="user",
        overlaps="roles,users"
    )

    is_active = Column(Boolean, nullable=False, server_default=text("true"))

    # relationships ke domain lain
    hospital = relationship("Hospital", back_populates="users", foreign_keys=[hospital_id])
    admin_of_hospital = relationship("Hospital", back_populates="admin", foreign_keys="Hospital.admin_id")
    claims_as_doctor = relationship("Claim", back_populates="doctor", foreign_keys="Claim.doctor_id")
    visits = relationship("Visit", back_populates="doctor", foreign_keys="Visit.doctor_id")
    medical_records = relationship("MedicalRecord", back_populates="doctor", foreign_keys="MedicalRecord.doctor_id")
    medical_record_logs = relationship("MedicalRecordLog", back_populates="user", foreign_keys="MedicalRecordLog.updated_by")

    # === Helper Methods ===
    @property
    def role_names(self):
        """Return list of role names (multi-role aware)."""
        if self.roles and len(self.roles) > 0:
            return [r.name for r in self.roles]
        elif self.role:
            return [self.role]
        return []

    def has_role(self, role_name: str) -> bool:
        """Check if user has specific role."""
        return role_name in self.role_names

    def __repr__(self):
        return f"<User(name={self.name}, roles={self.role_names})>"


# =========================================
# ROLE
# =========================================
class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)   # doctor, coder, verificator, admin_rs, etc.
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default=text("true"))

    # relasi ke users
    users = relationship(
        "User",
        secondary="user_roles",
        back_populates="roles",
        overlaps="user_roles"
    )
    user_roles = relationship(
        "UserRole",
        back_populates="role",
        overlaps="roles,users"
    )

    def __repr__(self):
        return f"<Role(name={self.name})>"


# =========================================
# USER ↔ ROLE Bridge (many-to-many)
# =========================================
class UserRole(Base, HousekeepingMixin):
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, server_default=text("now()"))

    user = relationship(
        "User",
        back_populates="user_roles",
        overlaps="roles,users"
    )
    role = relationship(
        "Role",
        back_populates="user_roles",
        overlaps="roles,users"
    )

    def __repr__(self):
        return f"<UserRole(user_id={self.user_id}, role_id={self.role_id})>"
