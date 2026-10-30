from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.session import ClassSession
from app.models.attendance import AttendanceLog, AttendanceStatus
from app.schemas.analytics import (
    RealtimeAnalyticsResponse,
    RecentLogItem,
    ContinuousMonitoringBatchRequest,
    ContinuousMonitoringBatchResponse,
)

router = APIRouter(prefix="/analytics", tags=["Analytics & Telemetry"])


@router.get("/realtime", response_model=RealtimeAnalyticsResponse)
def get_realtime_analytics(
    session_id: Optional[int] = Query(None, description="Optional filter by specific class session"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns real-time aggregated attendance statistics, anti-spoof metrics,
    and recent biometric verification logs for live dashboard telemetry.
    """
    # 1. Total Enrolled Students
    total_students = db.query(User).filter(User.role == UserRole.STUDENT).count()

    # 2. Identify active or target session
    active_session = None
    if session_id:
        active_session = db.query(ClassSession).filter(ClassSession.id == session_id).first()
    else:
        active_session = db.query(ClassSession).filter(ClassSession.is_active == True).order_by(desc(ClassSession.start_time)).first()

    # 3. Base Query for Attendance Logs
    logs_query = db.query(AttendanceLog)
    if active_session:
        logs_query = logs_query.filter(AttendanceLog.session_id == active_session.id)

    # Calculate status counts
    present_count = logs_query.filter(AttendanceLog.status == AttendanceStatus.PRESENT).count()
    spoof_count = logs_query.filter(AttendanceLog.status == AttendanceStatus.SPOOF_DETECTED).count()
    absent_count = max(0, total_students - present_count)

    # Attendance & Rejection Rates
    attendance_rate = round((present_count / total_students * 100), 2) if total_students > 0 else 0.0
    total_scans = present_count + spoof_count
    spoof_rejection_rate = round((spoof_count / total_scans * 100), 2) if total_scans > 0 else 100.0

    # 4. Fetch the 10 most recent attendance events
    recent_records = (
        logs_query
        .order_by(desc(AttendanceLog.timestamp))
        .limit(10)
        .all()
    )

    recent_items = []
    for r in recent_records:
        student = db.query(User).filter(User.id == r.student_id).first()
        session_obj = db.query(ClassSession).filter(ClassSession.id == r.session_id).first()
        recent_items.append(
            RecentLogItem(
                id=r.id,
                student_name=student.name if student else f"Student #{r.student_id}",
                roll_number=student.roll_number if student else None,
                avatar_url=student.avatar_url if student else None,
                subject_name=session_obj.subject_name if session_obj else "General",
                timestamp=r.timestamp,
                status=r.status,
                confidence_score=r.confidence_score,
                verification_method=r.verification_method,
            )
        )

    return RealtimeAnalyticsResponse(
        active_session_id=active_session.id if active_session else None,
        active_subject=active_session.subject_name if active_session else None,
        total_students=total_students,
        present_count=present_count,
        absent_count=absent_count,
        spoof_count=spoof_count,
        attendance_rate=attendance_rate,
        spoof_rejection_rate=spoof_rejection_rate,
        last_updated=datetime.now(timezone.utc),
        recent_logs=recent_items,
    )


@router.get("/weekly")
def get_weekly_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns database-backed weekly attendance statistics (last 5 calendar days).
    """
    from datetime import timedelta
    today = datetime.now(timezone.utc).date()
    days = [today - timedelta(days=i) for i in range(4, -1, -1)]

    labels = [d.strftime("%A (%b %d)") for d in days]
    present_data = []
    absent_data = []
    spoof_data = []

    total_logs_found = 0
    for day in days:
        day_start = datetime(day.year, day.month, day.day, 0, 0, 0, tzinfo=timezone.utc)
        day_end = datetime(day.year, day.month, day.day, 23, 59, 59, tzinfo=timezone.utc)

        p = db.query(AttendanceLog).filter(
            AttendanceLog.timestamp >= day_start,
            AttendanceLog.timestamp <= day_end,
            AttendanceLog.status == AttendanceStatus.PRESENT
        ).count()

        a = db.query(AttendanceLog).filter(
            AttendanceLog.timestamp >= day_start,
            AttendanceLog.timestamp <= day_end,
            AttendanceLog.status == AttendanceStatus.ABSENT
        ).count()

        s = db.query(AttendanceLog).filter(
            AttendanceLog.timestamp >= day_start,
            AttendanceLog.timestamp <= day_end,
            AttendanceLog.status == AttendanceStatus.SPOOF_DETECTED
        ).count()

        present_data.append(p)
        absent_data.append(a)
        spoof_data.append(s)
        total_logs_found += (p + a + s)

    return {
        "labels": labels,
        "present": present_data,
        "absent": absent_data,
        "spoof": spoof_data,
        "has_real_history": total_logs_found > 0,
        "total_records": total_logs_found,
        "note": "Actual SQLite records from attendx.db" if total_logs_found > 0 else "No real attendance data available yet."
    }



@router.post("/continuous-monitoring", response_model=ContinuousMonitoringBatchResponse)
def receive_continuous_monitoring_batch(
    payload: ContinuousMonitoringBatchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Receives periodic CCTV batch updates (YOLOv8 seat presence + MediaPipe Pose attention scores).
    If a student bunks midway, their attendance status is updated to ABSENT with an audit flag.
    """
    session = db.query(ClassSession).filter(ClassSession.id == payload.session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Class session {payload.session_id} not found."
        )

    bunks_count = 0
    updated_count = 0

    for item in payload.students:
        updated_count += 1
        if item.bunk_detected:
            bunks_count += 1
            # Find the student's attendance log for this session and flag as ABSENT midway
            log = (
                db.query(AttendanceLog)
                .filter(
                    AttendanceLog.session_id == session.id,
                    AttendanceLog.student_id == item.student_id
                )
                .first()
            )
            if log:
                log.status = AttendanceStatus.ABSENT
                reason = item.flag_reason or f"BUNK_DETECTED: Vacated seat {item.seat_id or ''} midway at interval {payload.interval_index}"
                log.notes = f"{log.notes} | {reason}" if log.notes else reason
            else:
                # Create record indicating student left
                new_log = AttendanceLog(
                    student_id=item.student_id,
                    session_id=session.id,
                    timestamp=payload.timestamp,
                    status=AttendanceStatus.ABSENT,
                    confidence_score=0.0,
                    verification_method="CCTV_YOLO_BUNK_TRACKER",
                    notes=item.flag_reason or f"BUNK_DETECTED: Vacated seat {item.seat_id or ''} midway"
                )
                db.add(new_log)

    db.commit()

    return ContinuousMonitoringBatchResponse(
        status="PROCESSED",
        session_id=payload.session_id,
        interval_index=payload.interval_index,
        students_updated=updated_count,
        bunks_flagged=bunks_count,
        timestamp=datetime.now(timezone.utc),
    )

