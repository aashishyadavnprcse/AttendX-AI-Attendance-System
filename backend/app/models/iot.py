from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from app.db.session import Base


class IoTDevice(Base):
    __tablename__ = "iot_devices"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(64), unique=True, index=True, nullable=False)
    device_type = Column(String(40), nullable=False)  # ESP32_CAM, RFID_RC522, BLE_BEACON
    location_label = Column(String(120), default="Lab Block C, Room 402", nullable=False)
    status = Column(String(32), default="SIMULATED", nullable=False)  # LIVE_CONNECTED, SIMULATED, OFFLINE
    ip_address = Column(String(45), nullable=True)
    mac_address = Column(String(32), nullable=True)
    firmware_version = Column(String(32), default="v1.2.0-esp32", nullable=False)
    last_heartbeat_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class RFIDCardMapping(Base):
    __tablename__ = "rfid_card_mappings"

    id = Column(Integer, primary_key=True, index=True)
    card_uid = Column(String(64), unique=True, index=True, nullable=False)  # e.g. "E2:80:68:1A"
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    issued_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
