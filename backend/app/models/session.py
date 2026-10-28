from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.db.session import Base


class ClassSession(Base):
    __tablename__ = "class_sessions"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subject_name = Column(String(150), nullable=False, index=True)
    start_time = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    end_time = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, index=True, nullable=False)
    
    # Geofencing Anchor Coordinates & Radius
    classroom_latitude = Column(Float, default=37.7749, nullable=False)
    classroom_longitude = Column(Float, default=-122.4194, nullable=False)
    geofence_radius_meters = Column(Float, default=20.0, nullable=False)
    require_geofence = Column(Boolean, default=True, nullable=False)

    # Campus Network Restrictions
    allowed_ip_subnet = Column(String(120), nullable=True) # e.g. "192.168.1.0/24, 10.0.0.0/16"
    allowed_wifi_bssid = Column(String(64), nullable=True)  # e.g. "00:14:22:01:23:45"
    require_campus_network = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    teacher = relationship("User", back_populates="sessions_taught")
    attendance_logs = relationship("AttendanceLog", back_populates="session", cascade="all, delete-orphan")

