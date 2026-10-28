from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class SessionStartRequest(BaseModel):
    subject_name: str
    classroom_latitude: Optional[float] = 37.7749
    classroom_longitude: Optional[float] = -122.4194
    geofence_radius_meters: Optional[float] = 20.0
    require_geofence: Optional[bool] = True
    allowed_ip_subnet: Optional[str] = None
    allowed_wifi_bssid: Optional[str] = None
    require_campus_network: Optional[bool] = False


class SessionStopRequest(BaseModel):
    session_id: int


class SessionResponse(BaseModel):
    id: int
    teacher_id: int
    subject_name: str
    classroom_latitude: float
    classroom_longitude: float
    geofence_radius_meters: float
    require_geofence: bool
    allowed_ip_subnet: Optional[str] = None
    allowed_wifi_bssid: Optional[str] = None
    require_campus_network: bool
    start_time: datetime
    end_time: Optional[datetime] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
