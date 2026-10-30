from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.db.session import Base


class ParentNotification(Base):
    __tablename__ = "parent_notifications"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("class_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Recipient details
    recipient_type = Column(String(32), default="PARENT", nullable=False)  # STUDENT, PARENT
    recipient_name = Column(String(120), nullable=True)
    recipient_phone = Column(String(32), nullable=True)

    # Legacy parent fields preserved
    parent_name = Column(String(120), nullable=False)
    parent_phone = Column(String(32), nullable=False)

    alert_type = Column(String(64), nullable=False)  # UNEXCUSED_ABSENCE, LOW_ATTENDANCE_WARNING, SPOOF_ATTEMPT_FLAGGED
    channel = Column(String(32), default="SMS_MOCK", nullable=False)  # SMS, SMS_MOCK, EMAIL, EMAIL_SIMULATED
    delivery_provider = Column(String(64), default="SIMULATED_GATEWAY", nullable=False)
    message = Column(Text, nullable=False)
    attendance_rate = Column(String(32), nullable=True)
    status = Column(String(64), default="PREVIEW_DELIVERED", nullable=False)  # DELIVERED, PREVIEW_DELIVERED, PENDING, FAILED, CORRECTED_TO_PRESENT, PHONE_NOT_REGISTERED
    error_message = Column(Text, nullable=True)
    is_cancelled = Column(Boolean, default=False, nullable=False)
    retry_count = Column(Integer, default=0, nullable=False)
    sent_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
