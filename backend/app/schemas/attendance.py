from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.attendance import AttendanceStatus


class AttendanceVerifyRequest(BaseModel):
    session_id: int
    student_id: Optional[int] = None
    roll_number: Optional[str] = None
    embedding_vector: List[float] = Field(..., description="Facial embedding vector from AI vision model")
    latitude: Optional[float] = Field(None, description="GPS Latitude coordinate")
    longitude: Optional[float] = Field(None, description="GPS Longitude coordinate")
    accuracy_meters: Optional[float] = Field(None, description="GPS accuracy reading in meters")
    wifi_bssid: Optional[str] = Field(None, description="Connected Wi-Fi router BSSID MAC address")
    is_live: bool = Field(True, description="Liveness flag from anti-spoofing algorithm")
    liveness_score: Optional[float] = Field(1.0, ge=0.0, le=1.0, description="Confidence score from liveness detection")
    verification_method: Optional[str] = "FACE_BIOMETRIC_LIVENESS"


class ManualAttendanceRequest(BaseModel):
    student_id: int
    session_id: Optional[int] = None
    status: AttendanceStatus = AttendanceStatus.PRESENT
    notes: Optional[str] = "Manual entry by instructor"


class AttendanceVerifyResponse(BaseModel):
    log_id: int
    student_id: int
    student_name: str
    session_id: int
    status: AttendanceStatus
    confidence_score: float
    liveness_verified: bool
    distance_meters: Optional[float] = None
    geofence_verified: bool = True
    timestamp: datetime
    message: str


class AttendanceLogResponse(BaseModel):
    id: int
    student_id: int
    session_id: int
    timestamp: datetime
    status: AttendanceStatus
    confidence_score: float
    verification_method: str
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None
    distance_meters: Optional[float] = None
    liveness_score: Optional[float] = None

    class Config:
        from_attributes = True


class AttendanceReportItem(BaseModel):
    id: int
    student_id: int
    student_name: str
    roll_number: Optional[str] = None
    avatar_url: Optional[str] = None
    session_id: int
    subject_name: str
    timestamp: datetime
    status: AttendanceStatus
    confidence_score: float
    verification_method: str
    distance_meters: Optional[float] = None
    liveness_score: Optional[float] = None
    notes: Optional[str] = None


class AttendanceReportsSummary(BaseModel):
    total_records: int
    present_count: int
    absent_count: int
    spoof_count: int
    attendance_rate: float


class AttendanceReportsResponse(BaseModel):
    total_records: int
    page: int
    page_size: int
    total_pages: int
    summary: AttendanceReportsSummary
    records: List[AttendanceReportItem]
