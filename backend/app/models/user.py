import enum
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Enum, JSON, Text, Boolean
from sqlalchemy.orm import relationship
from app.db.session import Base


class UserRole(str, enum.Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=True)
    role = Column(Enum(UserRole, values_callable=lambda x: [e.value for e in x]), default=UserRole.STUDENT, nullable=False)
    roll_number = Column(String(64), unique=True, index=True, nullable=True)

    def __init__(self, **kwargs):
        # Reconcile password_hash and hashed_password seamlessly
        if "hashed_password" in kwargs and "password_hash" not in kwargs:
            kwargs["password_hash"] = kwargs["hashed_password"]
        elif "password_hash" in kwargs and "hashed_password" not in kwargs:
            kwargs["hashed_password"] = kwargs["password_hash"]
        super().__init__(**kwargs)

    @property
    def effective_password_hash(self) -> Optional[str]:
        return self.hashed_password or self.password_hash

    def check_password(self, plain_password: str) -> bool:
        stored = self.hashed_password or self.password_hash
        if not stored:
            return False
        from app.core.security import verify_password
        return verify_password(plain_password, stored)

    
    # Stores 128-d or 512-d facial embedding coordinates (JSON array of floats)
    embedding_vector = Column(JSON, nullable=True)
    avatar_url = Column(Text, nullable=True)

    # Student Contact Information
    phone = Column(String(32), nullable=True)  # E.164 or formatted string

    # Parent Contact Information (for Attendance Alerts)
    parent_name = Column(String(120), nullable=True)
    parent_phone = Column(String(32), nullable=True)  # E.164 format, e.g. "+1234567890"
    parent_notifications_enabled = Column(Boolean, default=True, nullable=False)
    last_parent_alert_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    sessions_taught = relationship("ClassSession", back_populates="teacher", cascade="all, delete-orphan")
    attendance_records = relationship("AttendanceLog", back_populates="student", cascade="all, delete-orphan")
