import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.attendance import AttendanceLog, AttendanceStatus
from app.models.notification import ParentNotification

router = APIRouter(prefix="/predictions", tags=["Predictive Analytics & Parent Notifications"])


class NotificationDispatchRequest(BaseModel):
    student_id: int
    alert_type: str = "LOW_ATTENDANCE_WARNING"  # LOW_ATTENDANCE_WARNING, SPOOF_ATTEMPT_FLAGGED, UNEXCUSED_ABSENCE
    channel: str = "SMS_MOCK"  # SMS_MOCK, EMAIL_SIMULATED
    custom_message: Optional[str] = None


@router.get("/risk-summary")
def get_attendance_risk_summary(
    threshold: float = Query(75.0, ge=10.0, le=100.0, description="Configurable attendance cutoff percentage"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Computes purely statistical attendance risk indicators per student.
    Strictly based on empirical attendance records against configurable threshold.
    Avoids psychological inferences or speculative claims.
    """
    students = db.query(User).filter(User.role == UserRole.STUDENT).all()
    total_enrolled = len(students)

    student_risk_list = []
    critical_count = 0
    at_risk_count = 0
    safe_count = 0

    for s in students:
        logs = db.query(AttendanceLog).filter(AttendanceLog.student_id == s.id).all()
        total_sessions = len(logs)
        present_sessions = sum(1 for l in logs if l.status == AttendanceStatus.PRESENT)
        spoof_sessions = sum(1 for l in logs if l.status == AttendanceStatus.SPOOF_DETECTED)
        absent_sessions = sum(1 for l in logs if l.status == AttendanceStatus.ABSENT)

        rate = round((present_sessions / total_sessions * 100), 1) if total_sessions > 0 else 0.0

        if rate < threshold or total_sessions == 0:
            risk_level = "CRITICAL"
            action_needed = f"Immediate Parent Alert & Counseling (Below {threshold}% Exam Threshold)"
            critical_count += 1
        elif threshold <= rate < (threshold + 10.0):
            risk_level = "AT_RISK"
            action_needed = f"Attendance Watchlist (Borderline {threshold}%-{threshold + 9.0}%)"
            at_risk_count += 1
        else:
            risk_level = "SAFE"
            action_needed = f"Good Standing (>= {threshold + 10.0}%)"
            safe_count += 1

        # Absence streak calculation
        sorted_logs = sorted(
            logs,
            key=lambda x: (x.timestamp.replace(tzinfo=timezone.utc) if x.timestamp and x.timestamp.tzinfo is None else (x.timestamp or datetime.min.replace(tzinfo=timezone.utc))),
            reverse=True
        )
        absence_streak = 0
        for l in sorted_logs:
            if l.status == AttendanceStatus.ABSENT:
                absence_streak += 1
            else:
                break

        recent_presents = sum(1 for l in sorted_logs[:3] if l.status == AttendanceStatus.PRESENT)
        if len(sorted_logs) < 2:
            trend = "NEW_STUDENT"
        elif recent_presents >= 2:
            trend = "STABLE_OR_IMPROVING"
        else:
            trend = "DECLINING"

        student_risk_list.append({
            "student_id": s.id,
            "name": s.name,
            "roll_number": s.roll_number,
            "total_sessions": total_sessions,
            "present_count": present_sessions,
            "absent_count": absent_sessions,
            "spoof_count": spoof_sessions,
            "absence_streak": absence_streak,
            "attendance_rate": rate,
            "risk_level": risk_level,
            "action_needed": action_needed,
            "attendance_trend": trend,
            "parent_name": s.parent_name or "Not Enrolled",
            "parent_phone": s.parent_phone or "Not Enrolled",
            "last_alert_at": s.last_parent_alert_at.isoformat() if s.last_parent_alert_at else None
        })

    return {
        "status": "COMPUTED",
        "total_evaluated_students": total_enrolled,
        "configured_threshold_percent": threshold,
        "prediction_type": "RULE_BASED_STATISTICAL_INDICATOR (Empirical Attendance Rate)",
        "formula": "present_sessions / total_sessions * 100",
        "summary": {
            "critical_risk_count": critical_count,
            "at_risk_count": at_risk_count,
            "safe_count": safe_count,
            "threshold_criteria": f"Official {threshold}% Attendance Requirement for Course Examination"
        },
        "student_risks": student_risk_list,
        "evaluated_at": datetime.now(timezone.utc).isoformat()
    }


@router.get("/student/{student_id}")
def get_student_predictive_risk(
    student_id: int,
    threshold: float = Query(75.0, ge=10.0, le=100.0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns student-specific attendance statistics, streak indicators, and alert eligibility."""
    student = db.query(User).filter(User.id == student_id, User.role == UserRole.STUDENT).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    logs = db.query(AttendanceLog).filter(AttendanceLog.student_id == student.id).all()
    total = len(logs)
    presents = sum(1 for l in logs if l.status == AttendanceStatus.PRESENT)
    rate = round((presents / total * 100), 1) if total > 0 else 0.0

    return {
        "student_id": student.id,
        "name": student.name,
        "roll_number": student.roll_number,
        "total_sessions": total,
        "present_count": presents,
        "attendance_rate": rate,
        "threshold": threshold,
        "is_below_threshold": rate < threshold,
        "risk_level": "CRITICAL" if rate < threshold else ("AT_RISK" if rate < threshold + 10 else "SAFE"),
        "parent_contact": {
            "name": student.parent_name,
            "phone": student.parent_phone,
            "last_alert_at": student.last_parent_alert_at.isoformat() if student.last_parent_alert_at else None
        }
    }



@router.post("/dispatch-alert")
def dispatch_parent_alert(
    payload: NotificationDispatchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Dispatches a parent alert (SMS/Email mock gateway) and logs it into SQLite.
    Triggers automatically when student falls below 75% or presentation attack occurs.
    """
    student = db.query(User).filter(User.id == payload.student_id, User.role == UserRole.STUDENT).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student {payload.student_id} not found."
        )

    parent_name = student.parent_name or f"Parent of {student.name}"
    parent_phone = student.parent_phone or "+1 (555) 019-2831"

    logs = db.query(AttendanceLog).filter(AttendanceLog.student_id == student.id).all()
    total = len(logs)
    presents = sum(1 for l in logs if l.status == AttendanceStatus.PRESENT)
    rate = f"{round((presents / total * 100), 1)}%" if total > 0 else "0.0%"

    if payload.custom_message:
        msg = payload.custom_message
    elif payload.alert_type == "SPOOF_ATTEMPT_FLAGGED":
        msg = f"[AttendX Alert] Biometric spoofing attempt intercepted for {student.name} ({student.roll_number}). Physical presence required."
    else:
        msg = f"[AttendX Alert] Dear {parent_name}, {student.name}'s attendance has dropped to {rate} (below the mandatory 75% exam cutoff). Please coordinate with faculty."

    now = datetime.now(timezone.utc)
    
    # Provider Check: SMTP Email or Twilio SMS
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM", smtp_user or "notifications@attendx.ai")

    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_from = os.getenv("TWILIO_FROM_NUMBER")

    delivery_status = "PREVIEW_DELIVERED"
    gateway_status = "PREVIEW_MODE (CARRIER_NOT_CONFIGURED)"
    gateway_note = "Actual delivery requires TWILIO_ACCOUNT_SID or SMTP_HOST configuration in backend/.env."

    if payload.channel in ["EMAIL", "EMAIL_SMTP"] and smtp_host and smtp_user and smtp_password:
        try:
            mime_msg = MIMEText(msg)
            mime_msg["Subject"] = f"AttendX Alert: Attendance Notice for {student.name}"
            mime_msg["From"] = smtp_from
            mime_msg["To"] = student.email or "parent@attendx.ai"
            with smtplib.SMTP(smtp_host, smtp_port, timeout=5) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(mime_msg)
            delivery_status = "SENT"
            gateway_status = "SMTP_GATEWAY_SUCCESS"
            gateway_note = f"Dispatched via SMTP relay to {student.email}."
        except Exception as e:
            delivery_status = "FAILED"
            gateway_status = "SMTP_GATEWAY_ERROR"
            gateway_note = f"SMTP transmission failed: {type(e).__name__}."
    else:
        # Reuses the unified SMS gateway
        from app.services.notification_dispatcher import send_sms_notification
        sms_res = send_sms_notification(parent_phone, msg)
        delivery_status = sms_res["status"]
        gateway_status = sms_res["provider"]
        gateway_note = sms_res.get("error") or "Processed via unified AttendX SMS gateway."

    notification = ParentNotification(
        student_id=student.id,
        recipient_type="PARENT",
        recipient_name=parent_name,
        recipient_phone=parent_phone,
        parent_name=parent_name,
        parent_phone=parent_phone,
        alert_type=payload.alert_type,
        channel=payload.channel,
        delivery_provider=gateway_status,
        message=msg,
        attendance_rate=rate,
        status=delivery_status,
        error_message=gateway_note,
        is_cancelled=False,
        retry_count=0,
        sent_at=now
    )
    student.last_parent_alert_at = now
    db.add(notification)
    db.commit()
    db.refresh(notification)
    db.commit()
    db.refresh(notification)

    return {
        "status": delivery_status,
        "notification_id": notification.id,
        "student_id": student.id,
        "student_name": student.name,
        "recipient_phone": parent_phone,
        "channel": payload.channel,
        "message": msg,
        "delivered_at": now.isoformat(),
        "gateway_status": gateway_status,
        "gateway_note": gateway_note
    }


@router.get("/history")
def get_notification_history(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves chronological dispatch log of parent alerts."""
    records = db.query(ParentNotification).order_by(desc(ParentNotification.sent_at)).limit(limit).all()
    items = []
    for r in records:
        student = db.query(User).filter(User.id == r.student_id).first()
        items.append({
            "id": r.id,
            "student_id": r.student_id,
            "student_name": student.name if student else "Unknown",
            "roll_number": student.roll_number if student else "N/A",
            "parent_name": r.parent_name,
            "parent_phone": r.parent_phone,
            "alert_type": r.alert_type,
            "channel": r.channel,
            "message": r.message,
            "attendance_rate": r.attendance_rate,
            "status": r.status,
            "sent_at": r.sent_at.isoformat()
        })

    return {
        "total_dispatches": len(items),
        "total_logged": len(items),
        "history": items,
        "records": items
    }


class RetrySMSRequest(BaseModel):
    notification_id: int


@router.post("/retry-sms")
def retry_sms_endpoint(
    payload: RetrySMSRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retries sending an SMS for a failed or simulated notification dispatch.
    """
    from app.services.notification_dispatcher import retry_sms_notification
    result = retry_sms_notification(db, payload.notification_id)
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "SMS retry failed.")
        )
    return result


@router.get("/absent-alerts")
def get_absent_alerts(
    session_id: Optional[int] = Query(None, description="Optional class session ID filter"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves absent student notifications with privacy-masked phone numbers,
    delivery statuses, carrier/simulated indicators, and retry metrics.
    """
    from app.services.notification_dispatcher import mask_phone_number
    from app.models.session import ClassSession

    query = db.query(ParentNotification).filter(ParentNotification.alert_type == "UNEXCUSED_ABSENCE")
    if session_id:
        query = query.filter(ParentNotification.session_id == session_id)

    records = query.order_by(desc(ParentNotification.sent_at)).limit(limit).all()

    items = []
    for r in records:
        student = db.query(User).filter(User.id == r.student_id).first()
        sess = db.query(ClassSession).filter(ClassSession.id == r.session_id).first() if r.session_id else None

        phone_to_mask = r.recipient_phone or (student.phone if r.recipient_type == "STUDENT" else r.parent_phone)
        items.append({
            "id": r.id,
            "session_id": r.session_id,
            "subject_name": sess.subject_name if sess else "General Session",
            "student_id": r.student_id,
            "student_name": student.name if student else "Unknown",
            "roll_number": student.roll_number if student else "N/A",
            "recipient_type": r.recipient_type or "STUDENT",
            "recipient_name": r.recipient_name or (student.name if student else "Recipient"),
            "recipient_phone_masked": mask_phone_number(phone_to_mask),
            "status": r.status,
            "delivery_provider": r.delivery_provider or "SIMULATED_GATEWAY",
            "message": r.message,
            "error_message": r.error_message,
            "is_cancelled": bool(r.is_cancelled),
            "retry_count": r.retry_count or 0,
            "sent_at": r.sent_at.isoformat()
        })

    return {
        "total_absent_notifications": len(items),
        "alerts": items
    }

