from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from app.models.attendance import AttendanceStatus


class RecentLogItem(BaseModel):
    id: int
    student_name: str
    roll_number: Optional[str] = None
    avatar_url: Optional[str] = None
    subject_name: str
    timestamp: datetime
    status: AttendanceStatus
    confidence_score: float
    verification_method: str


class RealtimeAnalyticsResponse(BaseModel):
    active_session_id: Optional[int] = None
    active_subject: Optional[str] = None
    total_students: int
    present_count: int
    absent_count: int
    spoof_count: int
    attendance_rate: float  # Percentage, e.g. 94.5%
    spoof_rejection_rate: float
    last_updated: datetime
    recent_logs: List[RecentLogItem]


class StudentMonitoringUpdate(BaseModel):
    student_id: int
    roll_number: Optional[str] = None
    seat_id: Optional[str] = None
    is_present: bool
    bunk_detected: bool = False
    attention_score: float = 1.0  # Range: 0.0 to 1.0
    head_pose_status: Optional[str] = "FACING_BOARD"
    flag_reason: Optional[str] = None


class ContinuousMonitoringBatchRequest(BaseModel):
    session_id: int
    timestamp: datetime
    interval_index: int
    students: List[StudentMonitoringUpdate]
    average_attention_score: Optional[float] = None
    occupied_seats: Optional[int] = None
    total_seats: Optional[int] = None


class ContinuousMonitoringBatchResponse(BaseModel):
    status: str = "PROCESSED"
    success: bool = True
    session_id: int
    interval_index: int
    students_updated: int
    bunks_flagged: int
    timestamp: datetime
    processed_count: int = 0
    alerts_triggered: int = 0
    message: str = "Batch processed successfully"
