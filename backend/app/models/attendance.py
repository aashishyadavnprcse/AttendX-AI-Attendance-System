import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Enum, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.session import Base


class AttendanceStatus(str, enum.Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    SPOOF_DETECTED = "SPOOF_DETECTED"


class AttendanceLog(Base):
    __tablename__ = "attendance_logs"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("class_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    status = Column(Enum(AttendanceStatus), default=AttendanceStatus.PRESENT, nullable=False, index=True)
    confidence_score = Column(Float, nullable=False, default=0.0)
    verification_method = Column(String(80), default="FACE_BIOMETRIC_LIVENESS", nullable=False)
    
    # Geolocation & Network Telemetry
    gps_latitude = Column(Float, nullable=True)
    gps_longitude = Column(Float, nullable=True)
    distance_meters = Column(Float, nullable=True)
    client_ip = Column(String(45), nullable=True)
    wifi_bssid = Column(String(64), nullable=True)
    
    # Security / Anti-Spoof telemetry
    liveness_score = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    student = relationship("User", back_populates="attendance_records")
    session = relationship("ClassSession", back_populates="attendance_logs")
