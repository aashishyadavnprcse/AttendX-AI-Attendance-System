from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.dependencies import get_current_user, require_role
from app.core.security import get_password_hash
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.session import ClassSession
from app.models.attendance import AttendanceLog, AttendanceStatus
from app.schemas.user import StudentCreate, StudentListItem

router = APIRouter(prefix="/students", tags=["Student Management"])


@router.get("", response_model=List[StudentListItem])
def list_students(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all enrolled students along with their current session attendance status.
    """
    # 1. Fetch active class session if any
    active_session = db.query(ClassSession).filter(ClassSession.is_active == True).order_by(desc(ClassSession.start_time)).first()

    # 2. Fetch all student accounts
    students = db.query(User).filter(User.role == UserRole.STUDENT).order_by(User.name).all()

    result: List[StudentListItem] = []
    for s in students:
        session_status = "PENDING"
        confidence_score = None
        distance_meters = None
        last_verified_at = None

        if active_session:
            log = (
                db.query(AttendanceLog)
                .filter(
                    AttendanceLog.session_id == active_session.id,
                    AttendanceLog.student_id == s.id
                )
                .order_by(desc(AttendanceLog.timestamp))
                .first()
            )
            if log:
                session_status = log.status.value if hasattr(log.status, "value") else str(log.status)
                confidence_score = log.confidence_score
                distance_meters = log.distance_meters
                last_verified_at = log.timestamp
            else:
                session_status = "ABSENT / PENDING"

        result.append(
            StudentListItem(
                id=s.id,
                name=s.name,
                email=s.email,
                role=s.role.value if hasattr(s.role, "value") else str(s.role),
                roll_number=s.roll_number,
                avatar_url=s.avatar_url,
                phone=s.phone,
                parent_name=s.parent_name,
                parent_phone=s.parent_phone,
                parent_notifications_enabled=bool(s.parent_notifications_enabled if s.parent_notifications_enabled is not None else True),
                has_biometric_enrolled=bool(s.embedding_vector),
                session_status=session_status,
                confidence_score=confidence_score,
                distance_meters=distance_meters,
                last_verified_at=last_verified_at,
            )
        )

    return result


@router.post("", response_model=StudentListItem, status_code=status.HTTP_201_CREATED)
def create_student(
    payload: StudentCreate,
    current_user: User = Depends(require_role([UserRole.TEACHER, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    Enroll a new student in the database.
    Ensures email and roll_number uniqueness.
    """
    # Check email duplicate
    existing_email = db.query(User).filter(User.email == payload.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A student with email '{payload.email}' is already registered."
        )

    # Check roll number duplicate
    existing_roll = db.query(User).filter(User.roll_number == payload.roll_number).first()
    if existing_roll:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Roll number '{payload.roll_number}' is already assigned to {existing_roll.name}."
        )

    # Generate standard 128-d synthetic embedding coordinates for biometric matching demo
    synthetic_embedding = [0.04 * (i % 6) for i in range(128)]

    default_avatar = payload.avatar_url or "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150"

    new_student = User(
        name=payload.name,
        email=payload.email,
        hashed_password=get_password_hash(payload.password or "Student@123"),
        role=UserRole.STUDENT,
        roll_number=payload.roll_number,
        avatar_url=default_avatar,
        phone=payload.phone,
        parent_name=payload.parent_name,
        parent_phone=payload.parent_phone,
        parent_notifications_enabled=payload.parent_notifications_enabled if payload.parent_notifications_enabled is not None else True,
        embedding_vector=synthetic_embedding,
        created_at=datetime.now(timezone.utc),
    )

    db.add(new_student)
    db.commit()
    db.refresh(new_student)

    return StudentListItem(
        id=new_student.id,
        name=new_student.name,
        email=new_student.email,
        role=new_student.role.value if hasattr(new_student.role, "value") else str(new_student.role),
        roll_number=new_student.roll_number,
        avatar_url=new_student.avatar_url,
        phone=new_student.phone,
        parent_name=new_student.parent_name,
        parent_phone=new_student.parent_phone,
        parent_notifications_enabled=bool(new_student.parent_notifications_enabled),
        has_biometric_enrolled=True,
        session_status="ABSENT / PENDING",
        confidence_score=None,
        distance_meters=None,
        last_verified_at=None,
    )
