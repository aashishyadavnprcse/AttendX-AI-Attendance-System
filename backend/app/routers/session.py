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

    # Automatic Absent Student Notification Reconciliation
    try:
        from app.services.notification_dispatcher import process_session_absentees
        process_session_absentees(db, session, teacher_name=current_user.name)
    except Exception as e:
        import logging
        logging.getLogger("attendx.session").error(f"Automatic absent notification on stop_session error: {e}")

    return session


@router.post("/{session_id}/finalize-absentees")
def finalize_session_absentees_endpoint(
    session_id: int,
    current_user: User = Depends(require_role([UserRole.TEACHER, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    On-demand endpoint to reconcile absent students and dispatch SMS notifications
    without requiring a session status change.
    """
    session = db.query(ClassSession).filter(ClassSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    from app.services.notification_dispatcher import process_session_absentees
    summary = process_session_absentees(db, session, teacher_name=current_user.name)
    return summary


@router.get("/active", response_model=List[SessionResponse])
def get_active_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all currently ongoing active class sessions.
    """
    return db.query(ClassSession).filter(ClassSession.is_active == True).all()


@router.get("/current")
def get_current_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the currently active class session.
    """
    from sqlalchemy import desc
    active_session = db.query(ClassSession).filter(ClassSession.is_active == True).order_by(desc(ClassSession.start_time)).first()
    if not active_session:
        return {"is_active": False, "session": None}
    return {
        "is_active": True,
        "session": {
            "id": active_session.id,
            "subject_name": active_session.subject_name,
            "teacher_id": active_session.teacher_id,
            "classroom_latitude": active_session.classroom_latitude,
            "classroom_longitude": active_session.classroom_longitude,
            "geofence_radius_meters": active_session.geofence_radius_meters,
            "require_geofence": active_session.require_geofence,
            "start_time": active_session.start_time,
        }
    }


@router.post("/toggle")
def toggle_session(
    current_user: User = Depends(require_role([UserRole.TEACHER, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    Toggle active class session between Active and Concluded.
    """
    from sqlalchemy import desc
    active_session = db.query(ClassSession).filter(ClassSession.is_active == True).order_by(desc(ClassSession.start_time)).first()
    if active_session:
        active_session.is_active = False
        active_session.end_time = datetime.now(timezone.utc)
        db.commit()
        db.refresh(active_session)

        # Reconcile absent students and dispatch notifications
        absent_summary = {}
        try:
            from app.services.notification_dispatcher import process_session_absentees
            absent_summary = process_session_absentees(db, active_session, teacher_name=current_user.name)
        except Exception as e:
            import logging
            logging.getLogger("attendx.session").error(f"Absentee processing error on toggle: {e}")

        return {
            "is_active": False,
            "session_id": active_session.id,
            "subject_name": active_session.subject_name,
            "message": f"Concluded session '{active_session.subject_name}'. Absentee notification reconciliation completed.",
            "absentee_summary": absent_summary
        }
    else:
        latest_session = db.query(ClassSession).order_by(desc(ClassSession.id)).first()
        if latest_session:
            latest_session.is_active = True
            latest_session.start_time = datetime.now(timezone.utc)
            latest_session.end_time = None
            db.commit()
            db.refresh(latest_session)
            return {"is_active": True, "subject_name": latest_session.subject_name, "message": f"Activated session '{latest_session.subject_name}'."}
        else:
            new_session = ClassSession(
                teacher_id=current_user.id,
                subject_name="Neural Networks & Computer Vision",
                classroom_latitude=37.7749,
                classroom_longitude=-122.4194,
                geofence_radius_meters=20.0,
                is_active=True,
                start_time=datetime.now(timezone.utc),
            )
            db.add(new_session)
            db.commit()
            db.refresh(new_session)
            return {"is_active": True, "subject_name": new_session.subject_name, "message": f"Started session '{new_session.subject_name}'."}

