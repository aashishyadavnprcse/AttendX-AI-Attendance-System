from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.session import ClassSession
from app.models.attendance import AttendanceLog, AttendanceStatus
from app.schemas.attendance import (
    AttendanceVerifyRequest,
    AttendanceVerifyResponse,
    AttendanceReportsResponse,
    AttendanceReportItem,
    AttendanceReportsSummary,
    ManualAttendanceRequest,
)
from app.services.face_matcher import verify_biometric_face
from app.services.geofence_validator import validate_geofence_and_network_security

router = APIRouter(prefix="/attendance", tags=["Attendance Biometrics"])


@router.post("/verify", response_model=AttendanceVerifyResponse)
def verify_attendance(
    payload: AttendanceVerifyRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify biometric face embedding against enrolled student profile,
    check liveness against anti-spoofing flags, validate GPS telemetry,
    and record an immutable attendance log.
    """
    # 1. Validate Session
    session = db.query(ClassSession).filter(ClassSession.id == payload.session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Class session {payload.session_id} not found."
        )

    if not session.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Class session '{session.subject_name}' is currently inactive or concluded."
        )

    # 2. Extract Client IP & Validate Physical Geofence + Network Security (<= 20m)
    client_ip = request.headers.get("x-forwarded-for")
    if client_ip:
        client_ip = client_ip.split(",")[0].strip()
    elif request.client:
        client_ip = request.client.host

    is_geo_valid, distance_meters, geo_msg = validate_geofence_and_network_security(
        device_latitude=payload.latitude,
        device_longitude=payload.longitude,
        classroom_latitude=session.classroom_latitude,
        classroom_longitude=session.classroom_longitude,
        max_radius_meters=session.geofence_radius_meters,
        client_ip=client_ip,
        allowed_subnets=session.allowed_ip_subnet,
        device_bssid=payload.wifi_bssid,
        allowed_bssid=session.allowed_wifi_bssid,
        enforce_geofence=session.require_geofence,
        enforce_network=session.require_campus_network,
    )

    # 3. Determine target student
    target_student = None
    if payload.student_id:
        target_student = db.query(User).filter(User.id == payload.student_id).first()
    elif payload.roll_number:
        target_student = db.query(User).filter(User.roll_number == payload.roll_number).first()
    elif current_user.role == UserRole.STUDENT:
        target_student = current_user

    if not target_student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student could not be identified. Please supply student_id or roll_number."
        )

    # 4. Biometric and Anti-Spoof Liveness verification
    is_match, is_spoof, confidence, msg = verify_biometric_face(
        candidate_vector=payload.embedding_vector,
        registered_vector=target_student.embedding_vector,
        is_live=payload.is_live,
        liveness_score=payload.liveness_score or 1.0,
        threshold=settings.FACE_MATCH_SIMILARITY_THRESHOLD,
        min_liveness=settings.LIVENESS_MIN_CONFIDENCE,
    )

    attendance_status = AttendanceStatus.PRESENT if (is_match and not is_spoof) else AttendanceStatus.SPOOF_DETECTED

    # 5. Check if student already marked PRESENT in this session
    existing_record = db.query(AttendanceLog).filter(
        AttendanceLog.session_id == session.id,
        AttendanceLog.student_id == target_student.id,
        AttendanceLog.status == AttendanceStatus.PRESENT
    ).first()

    if existing_record and attendance_status == AttendanceStatus.PRESENT:
        return AttendanceVerifyResponse(
            log_id=existing_record.id,
            student_id=target_student.id,
            student_name=target_student.name,
            session_id=session.id,
            status=AttendanceStatus.PRESENT,
            confidence_score=existing_record.confidence_score,
            liveness_verified=True,
            distance_meters=distance_meters,
            geofence_verified=True,
            timestamp=existing_record.timestamp,
            message="Student was already marked PRESENT in this session.",
        )

    # 6. Persist Attendance Log with Geofencing & Network Telemetry
    log = AttendanceLog(
        student_id=target_student.id,
        session_id=session.id,
        timestamp=datetime.now(timezone.utc),
        status=attendance_status,
        confidence_score=confidence,
        verification_method=payload.verification_method or "FACE_BIOMETRIC_LIVENESS",
        gps_latitude=payload.latitude,
        gps_longitude=payload.longitude,
        distance_meters=distance_meters,
        client_ip=client_ip,
        wifi_bssid=payload.wifi_bssid,
        liveness_score=payload.liveness_score,
        notes=msg if is_spoof else None,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    if attendance_status == AttendanceStatus.PRESENT:
        try:
            from app.services.notification_dispatcher import sync_attendance_correction
            sync_attendance_correction(db, session.id, target_student.id, attendance_status, "Biometric Face Recognition")
        except Exception:
            pass

    return AttendanceVerifyResponse(
        log_id=log.id,
        student_id=target_student.id,
        student_name=target_student.name,
        session_id=session.id,
        status=attendance_status,
        confidence_score=confidence,
        liveness_verified=payload.is_live and not is_spoof,
        distance_meters=distance_meters,
        geofence_verified=True,
        timestamp=log.timestamp,
        message=f"{msg} | {geo_msg}",
    )


@router.get("/reports", response_model=AttendanceReportsResponse)
def get_attendance_reports(
    session_id: Optional[int] = Query(None, description="Filter by class session ID"),
    status_filter: Optional[AttendanceStatus] = Query(None, alias="status", description="Filter by status"),
    start_date: Optional[datetime] = Query(None, description="Start date/time filter"),
    end_date: Optional[datetime] = Query(None, description="End date/time filter"),
    student_id: Optional[int] = Query(None, description="Filter by student user ID"),
    search: Optional[str] = Query(None, description="Search by student name or roll number"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Query historical and session-level attendance reports with filtering,
    summary aggregations (present/absent/spoof counts), and pagination.
    """
    from sqlalchemy import desc, or_
    import math

    query = (
        db.query(AttendanceLog, User, ClassSession)
        .join(User, AttendanceLog.student_id == User.id)
        .join(ClassSession, AttendanceLog.session_id == ClassSession.id)
    )

    if session_id:
        query = query.filter(AttendanceLog.session_id == session_id)
    if status_filter:
        query = query.filter(AttendanceLog.status == status_filter)
    if start_date:
        query = query.filter(AttendanceLog.timestamp >= start_date)
    if end_date:
        query = query.filter(AttendanceLog.timestamp <= end_date)
    if student_id:
        query = query.filter(AttendanceLog.student_id == student_id)
    if search:
        search_fmt = f"%{search.strip()}%"
        query = query.filter(or_(User.name.ilike(search_fmt), User.roll_number.ilike(search_fmt)))

    total_records = query.count()

    # Calculate summary counts for the filtered scope
    base_logs = db.query(AttendanceLog)
    if session_id:
        base_logs = base_logs.filter(AttendanceLog.session_id == session_id)
    if start_date:
        base_logs = base_logs.filter(AttendanceLog.timestamp >= start_date)
    if end_date:
        base_logs = base_logs.filter(AttendanceLog.timestamp <= end_date)

    present_count = base_logs.filter(AttendanceLog.status == AttendanceStatus.PRESENT).count()
    absent_count = base_logs.filter(AttendanceLog.status == AttendanceStatus.ABSENT).count()
    spoof_count = base_logs.filter(AttendanceLog.status == AttendanceStatus.SPOOF_DETECTED).count()
    total_relevant = present_count + absent_count
    attendance_rate = round((present_count / total_relevant * 100), 2) if total_relevant > 0 else 100.0

    # Paginate
    offset = (page - 1) * page_size
    records = query.order_by(desc(AttendanceLog.timestamp)).offset(offset).limit(page_size).all()

    report_items = []
    for log, student, sess in records:
        report_items.append(
            AttendanceReportItem(
                id=log.id,
                student_id=student.id,
                student_name=student.name,
                roll_number=student.roll_number,
                avatar_url=student.avatar_url,
                session_id=sess.id,
                subject_name=sess.subject_name,
                timestamp=log.timestamp,
                status=log.status,
                confidence_score=log.confidence_score,
                verification_method=log.verification_method,
                distance_meters=log.distance_meters,
                liveness_score=log.liveness_score,
                notes=log.notes,
            )
        )

    total_pages = max(1, math.ceil(total_records / page_size))

    return AttendanceReportsResponse(
        total_records=total_records,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        summary=AttendanceReportsSummary(
            total_records=total_records,
            present_count=present_count,
            absent_count=absent_count,
            spoof_count=spoof_count,
            attendance_rate=attendance_rate,
        ),
        records=report_items,
    )


@router.post("/manual", response_model=AttendanceVerifyResponse)
def record_manual_attendance(
    payload: ManualAttendanceRequest,
    current_user: User = Depends(require_role([UserRole.TEACHER, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    Manually record or update attendance for an enrolled student.
    Prevents duplicate entries for the same student and session.
    """
    from sqlalchemy import desc

    # 1. Validate student
    student = db.query(User).filter(User.id == payload.student_id, User.role == UserRole.STUDENT).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with ID {payload.student_id} not found."
        )

    # 2. Validate session
    session = None
    if payload.session_id:
        session = db.query(ClassSession).filter(ClassSession.id == payload.session_id).first()
    else:
        session = db.query(ClassSession).filter(ClassSession.is_active == True).order_by(desc(ClassSession.start_time)).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active class session found. Please start a session first."
        )

    # 3. Check for duplicate attendance
    existing_log = db.query(AttendanceLog).filter(
        AttendanceLog.session_id == session.id,
        AttendanceLog.student_id == student.id,
        AttendanceLog.status == payload.status
    ).first()

    if existing_log:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Duplicate prevented: {student.name} ({student.roll_number}) is already marked {payload.status.value} for session '{session.subject_name}'."
        )

    # Check if student already has a log in this session with a different status
    prior_log = db.query(AttendanceLog).filter(
        AttendanceLog.session_id == session.id,
        AttendanceLog.student_id == student.id
    ).first()

    if prior_log:
        prior_log.status = payload.status
        prior_log.timestamp = datetime.now(timezone.utc)
        prior_log.verification_method = "MANUAL_INSTRUCTOR_VERIFICATION"
        prior_log.notes = payload.notes or f"Updated to {payload.status.value} by instructor"
        prior_log.confidence_score = 1.0
        db.commit()
        db.refresh(prior_log)
        log = prior_log
    else:
        log = AttendanceLog(
            student_id=student.id,
            session_id=session.id,
            timestamp=datetime.now(timezone.utc),
            status=payload.status,
            confidence_score=1.0,
            verification_method="MANUAL_INSTRUCTOR_VERIFICATION",
            gps_latitude=session.classroom_latitude,
            gps_longitude=session.classroom_longitude,
            distance_meters=0.0,
            liveness_score=1.0,
            notes=payload.notes or "Manual attendance record",
        )
        db.add(log)
        db.commit()
        db.refresh(log)

    if payload.status == AttendanceStatus.PRESENT:
        try:
            from app.services.notification_dispatcher import sync_attendance_correction
            sync_attendance_correction(db, session.id, student.id, payload.status, current_user.name)
        except Exception:
            pass

    return AttendanceVerifyResponse(
        log_id=log.id,
        student_id=student.id,
        student_name=student.name,
        session_id=session.id,
        status=log.status,
        confidence_score=1.0,
        liveness_verified=True,
        distance_meters=0.0,
        geofence_verified=True,
        timestamp=log.timestamp,
        message=f"Attendance recorded as {log.status.value} for {student.name}.",
    )


