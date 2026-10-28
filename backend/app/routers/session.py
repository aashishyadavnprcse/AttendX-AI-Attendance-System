from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.session import ClassSession
from app.schemas.session import SessionStartRequest, SessionStopRequest, SessionResponse

router = APIRouter(prefix="/session", tags=["Class Sessions"])


@router.post("/start", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def start_session(
    payload: SessionStartRequest,
    current_user: User = Depends(require_role([UserRole.TEACHER, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    Start a live attendance class session for a given subject.
    Only teachers and admins are authorized.
    """
    # Check if there is already an active session for this teacher with the same subject
    existing_active = db.query(ClassSession).filter(
        ClassSession.teacher_id == current_user.id,
        ClassSession.subject_name == payload.subject_name,
        ClassSession.is_active == True,
    ).first()

    if existing_active:
        return existing_active

    new_session = ClassSession(
        teacher_id=current_user.id,
        subject_name=payload.subject_name,
        classroom_latitude=payload.classroom_latitude or 37.7749,
        classroom_longitude=payload.classroom_longitude or -122.4194,
        geofence_radius_meters=payload.geofence_radius_meters or 20.0,
        require_geofence=payload.require_geofence if payload.require_geofence is not None else True,
        allowed_ip_subnet=payload.allowed_ip_subnet,
        allowed_wifi_bssid=payload.allowed_wifi_bssid,
        require_campus_network=payload.require_campus_network or False,
        start_time=datetime.now(timezone.utc),
        is_active=True,
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session


@router.post("/stop", response_model=SessionResponse)
def stop_session(
    payload: SessionStopRequest,
    current_user: User = Depends(require_role([UserRole.TEACHER, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    Stop an active attendance class session.
    """
    session = db.query(ClassSession).filter(ClassSession.id == payload.session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID {payload.session_id} not found."
        )

    # Teachers can only stop their own sessions; admins can stop any
    if current_user.role == UserRole.TEACHER and session.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are only authorized to conclude sessions you initiated."
        )

    if not session.is_active:
        return session

    session.is_active = False
    session.end_time = datetime.now(timezone.utc)
    db.commit()
    db.refresh(session)
    return session


@router.get("/active", response_model=List[SessionResponse])
def get_active_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all currently ongoing active class sessions.
    """
    return db.query(ClassSession).filter(ClassSession.is_active == True).all()
