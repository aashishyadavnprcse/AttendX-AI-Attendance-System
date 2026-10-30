import hashlib
import json
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text
from app.db.session import Base


class AttendanceAuditLedger(Base):
    __tablename__ = "attendance_audit_ledger"

    id = Column(Integer, primary_key=True, index=True)
    block_index = Column(Integer, unique=True, index=True, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    log_id = Column(Integer, nullable=True, index=True)
    student_id = Column(Integer, nullable=True, index=True)
    action = Column(String(64), nullable=False)  # ATTENDANCE_RECORDED, STATUS_MODIFIED, SPOOF_INTERCEPTED, GEOFENCE_VIOLATION
    payload_snapshot = Column(Text, nullable=False)  # JSON snapshot of data
    previous_hash = Column(String(64), nullable=False)
    current_hash = Column(String(64), nullable=False, unique=True, index=True)
    blockchain_tx_receipt = Column(String(128), nullable=True)  # Mock testnet transaction anchor or hash

    @staticmethod
    def calculate_hash(block_index: int, timestamp: any, action: str, payload: str, previous_hash: str) -> str:
        if isinstance(timestamp, datetime):
            time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        else:
            time_str = str(timestamp).split(".")[0].replace("T", " ")
        raw_string = f"{block_index}:{time_str}:{action}:{payload}:{previous_hash}"
        return hashlib.sha256(raw_string.encode("utf-8")).hexdigest()
