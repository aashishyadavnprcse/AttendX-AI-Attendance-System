import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Enum, JSON, Text
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
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.STUDENT, nullable=False)
    roll_number = Column(String(64), unique=True, index=True, nullable=True)
    
    # Stores 128-d or 512-d facial embedding coordinates (JSON array of floats)
    embedding_vector = Column(JSON, nullable=True)
    avatar_url = Column(Text, nullable=True)

    # Parent Contact Information (for Attendance Alerts)
    parent_name = Column(String(120), nullable=True)
    parent_phone = Column(String(32), nullable=True)  # E.164 format, e.g. "+1234567890"
    last_parent_alert_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    sessions_taught = relationship("ClassSession", back_populates="teacher", cascade="all, delete-orphan")
    attendance_records = relationship("AttendanceLog", back_populates="student", cascade="all, delete-orphan")
