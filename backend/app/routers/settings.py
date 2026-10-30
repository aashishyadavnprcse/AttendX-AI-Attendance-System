from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.config import settings
from app.core.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.session import ClassSession
from app.schemas.settings import SystemSettingsResponse, SettingsUpdateRequest

router = APIRouter(prefix="/settings", tags=["System Settings"])


@router.get("", response_model=SystemSettingsResponse)
def get_system_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current system parameters, AI thresholds, and active session configuration.
    """
    active_session = db.query(ClassSession).filter(ClassSession.is_active == True).order_by(desc(ClassSession.start_time)).first()

    return SystemSettingsResponse(
        project_name=settings.PROJECT_NAME,
        api_base_url="http://127.0.0.1:8765/api",
        geofence_radius_meters=active_session.geofence_radius_meters if active_session else 20.0,
        face_match_threshold=settings.FACE_MATCH_SIMILARITY_THRESHOLD,
        liveness_min_confidence=settings.LIVENESS_MIN_CONFIDENCE,
        jwt_access_token_expire_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        active_subject=active_session.subject_name if active_session else "No Active Session",
        active_session_id=active_session.id if active_session else None,
        is_session_active=bool(active_session and active_session.is_active),
        classroom_coordinates=f"{active_session.classroom_latitude}° N, {active_session.classroom_longitude}° W" if active_session else "37.7749° N, -122.4194° W",
    )


@router.post("", response_model=SystemSettingsResponse)
def update_system_settings(
    payload: SettingsUpdateRequest,
    current_user: User = Depends(require_role([UserRole.TEACHER, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    Update configuration for the current active session.
    """
    active_session = db.query(ClassSession).filter(ClassSession.is_active == True).order_by(desc(ClassSession.start_time)).first()
    if not active_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active session found to configure. Please start a session first."
        )

    if payload.geofence_radius_meters is not None:
        active_session.geofence_radius_meters = payload.geofence_radius_meters
    if payload.subject_name is not None and payload.subject_name.strip():
        active_session.subject_name = payload.subject_name.strip()

    db.commit()
    db.refresh(active_session)

    return SystemSettingsResponse(
        project_name=settings.PROJECT_NAME,
        api_base_url="http://127.0.0.1:8765/api",
        geofence_radius_meters=active_session.geofence_radius_meters,
        face_match_threshold=settings.FACE_MATCH_SIMILARITY_THRESHOLD,
        liveness_min_confidence=settings.LIVENESS_MIN_CONFIDENCE,
        jwt_access_token_expire_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        active_subject=active_session.subject_name,
        active_session_id=active_session.id,
        is_session_active=active_session.is_active,
        classroom_coordinates=f"{active_session.classroom_latitude}° N, {active_session.classroom_longitude}° W",
    )
