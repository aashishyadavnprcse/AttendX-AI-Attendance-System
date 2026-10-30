from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class SystemSettingsResponse(BaseModel):
    project_name: str
    api_base_url: str
    geofence_radius_meters: float
    face_match_threshold: float
    liveness_min_confidence: float
    jwt_access_token_expire_minutes: int
    active_subject: Optional[str] = None
    active_session_id: Optional[int] = None
    is_session_active: bool = False
    classroom_coordinates: str


class SettingsUpdateRequest(BaseModel):
    geofence_radius_meters: Optional[float] = None
    subject_name: Optional[str] = None
