"""
AttendX AI — Unified Notification Gateway & Absentee Dispatcher
Handles automatic absent reconciliation on session conclusion,
unified SMS carrier dispatch (Twilio / Fast2SMS) with transparent PREVIEW_MODE fallback,
phone privacy masking, duplicate suppression, and attendance correction synchronization.
"""

import os
import re
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from app.models.session import ClassSession
from app.models.attendance import AttendanceLog, AttendanceStatus
from app.models.notification import ParentNotification

logger = logging.getLogger("attendx.notifications")


def mask_phone_number(phone: Optional[str]) -> str:
    """
    Masks a phone number for privacy display (e.g. '+91 98*** **210' or '+1 (415) ***-2671').
    Keeps international prefix and last 3-4 digits visible.
    """
    if not phone or not phone.strip():
        return "NOT_REGISTERED"
    
    clean = phone.strip()
    digits_only = re.sub(r"\D", "", clean)
    if len(digits_only) < 7:
        return clean[:2] + "****" + clean[-2:] if len(clean) >= 4 else "****"

    if clean.startswith("+91") or (len(digits_only) == 10 and clean.startswith("9")):
        if clean.startswith("+91"):
            num = digits_only[2:] if len(digits_only) > 10 else digits_only
        else:
            num = digits_only
        if len(num) >= 10:
            return f"+91 {num[:2]}*** **{num[-3:]}"
    
    if len(clean) > 8:
        return f"{clean[:4]}****{clean[-4:]}"
    return f"{clean[:2]}****{clean[-2:]}"


def send_sms_notification(to_phone: Optional[str], message: str) -> Dict[str, Any]:
    """
    Unified SMS Gateway:
    - If phone number is missing: returns status 'MISSING_PHONE'.
    - If real carrier (Twilio / Fast2SMS) is configured: dispatches carrier SMS.
      Returns status 'SENT' (or 'FAILED' on error).
    - If no real carrier is configured: transparently returns status 'PREVIEW'.
      Never claims actual cellular delivery without credentials.
    """
    if not to_phone or not to_phone.strip():
        return {
            "status": "MISSING_PHONE",
            "provider": "NONE",
            "message_id": None,
            "error": "Recipient phone number is not registered."
        }

    phone_clean = to_phone.strip()

    # 1. Check Twilio Carrier Credentials
    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_from = os.getenv("TWILIO_FROM_NUMBER")

    if twilio_sid and twilio_token and twilio_from:
        try:
            import requests
            resp = requests.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json",
                data={"From": twilio_from, "To": phone_clean, "Body": message},
                auth=(twilio_sid, twilio_token),
                timeout=8
            )
            if resp.status_code in (200, 201):
                res_data = resp.json()
                return {
                    "status": "SENT",
                    "provider": "TWILIO_CARRIER",
                    "message_id": res_data.get("sid", str(uuid.uuid4())),
                    "error": None
                }
            else:
                return {
                    "status": "FAILED",
                    "provider": "TWILIO_CARRIER",
                    "message_id": None,
                    "error": f"Twilio HTTP {resp.status_code}: {resp.text}"
                }
        except Exception as e:
            logger.error(f"[SMS Gateway] Twilio error: {e}")
            return {
                "status": "FAILED",
                "provider": "TWILIO_CARRIER",
                "message_id": None,
                "error": f"Twilio connection error: {str(e)}"
            }

    # 2. Check Fast2SMS Carrier Credentials
    fast2sms_key = os.getenv("FAST2SMS_API_KEY")
    if fast2sms_key:
        try:
            import requests
            digits = re.sub(r"\D", "", phone_clean)
            if digits.startswith("91") and len(digits) == 12:
                digits = digits[2:]
            headers = {
                "authorization": fast2sms_key,
                "Content-Type": "application/json"
            }
            body = {
                "route": "q",
                "message": message,
                "language": "english",
                "flash": 0,
                "numbers": digits
            }
            resp = requests.post("https://www.fast2sms.com/dev/bulkV2", json=body, headers=headers, timeout=8)
            if resp.status_code == 200 and resp.json().get("return"):
                return {
                    "status": "SENT",
                    "provider": "FAST2SMS_CARRIER",
                    "message_id": resp.json().get("request_id", str(uuid.uuid4())),
                    "error": None
                }
            else:
                return {
                    "status": "FAILED",
                    "provider": "FAST2SMS_CARRIER",
                    "message_id": None,
                    "error": f"Fast2SMS error: {resp.text}"
                }
        except Exception as e:
            logger.error(f"[SMS Gateway] Fast2SMS error: {e}")
            return {
                "status": "FAILED",
                "provider": "FAST2SMS_CARRIER",
                "message_id": None,
                "error": f"Fast2SMS connection error: {str(e)}"
            }

    # 3. Transparent Mock / Preview Mode (Safe Fallback)
    mock_id = f"PREVIEW-{uuid.uuid4().hex[:10].upper()}"
    return {
        "status": "PREVIEW",
        "provider": "PREVIEW_MODE (PROVIDER_NOT_CONFIGURED)",
        "message_id": mock_id,
        "error": "No SMS carrier credentials configured in environment. Logged in preview mode."
    }


def process_session_absentees(db: Session, session: ClassSession, teacher_name: Optional[str] = None) -> Dict[str, Any]:
    """
    On session close/stop:
    1. Compares all enrolled students against attendance logs for this session.
    2. Identifies confirmed absent students (not marked PRESENT).
    3. Auto-marks unrecorded students as ABSENT in AttendanceLog.
    4. Generates absent notification for student's registered mobile number.
    5. Generates parent notification if parent contact is registered and notification is enabled.
    6. Formats message with: student name, class, subject, date, and attendance status.
    7. Strictly prevents duplicate notifications for the same student and session.
    """
    students = db.query(User).filter(User.role == UserRole.STUDENT).all()
    teacher_label = teacher_name or (session.teacher.name if session.teacher else "Faculty Member")
    session_date_str = session.start_time.strftime("%d-%b-%Y %I:%M %p")
    class_code = session.subject_name.split()[0] if session.subject_name else "CS-Cohort"

    results = {
        "session_id": session.id,
        "subject_name": session.subject_name,
        "total_enrolled_students": len(students),
        "present_count": 0,
        "absent_count": 0,
        "newly_marked_absent": 0,
        "student_notifications_sent": 0,
        "parent_notifications_sent": 0,
        "duplicates_prevented": 0,
        "details": []
    }

    for student in students:
        # Check existing attendance log in this session
        existing_log = db.query(AttendanceLog).filter(
            AttendanceLog.session_id == session.id,
            AttendanceLog.student_id == student.id
        ).first()

        # If student is already PRESENT, skip absent notification completely
        if existing_log and existing_log.status == AttendanceStatus.PRESENT:
            results["present_count"] += 1
            results["details"].append({
                "student_id": student.id,
                "student_name": student.name,
                "status": "PRESENT",
                "action": "SKIPPED_PRESENT"
            })
            continue

        # If student has no attendance record, record ABSENT
        if not existing_log:
            absent_log = AttendanceLog(
                student_id=student.id,
                session_id=session.id,
                timestamp=datetime.now(timezone.utc),
                status=AttendanceStatus.ABSENT,
                confidence_score=1.0,
                verification_method="AUTOMATIC_SESSION_RECONCILIATION",
                gps_latitude=session.classroom_latitude,
                gps_longitude=session.classroom_longitude,
                distance_meters=0.0,
                liveness_score=0.0,
                notes="Auto-marked ABSENT on session conclusion"
            )
            db.add(absent_log)
            db.flush()
            results["newly_marked_absent"] += 1

        results["absent_count"] += 1

        # Check duplicate notification prevention for this session & student
        existing_notif = db.query(ParentNotification).filter(
            ParentNotification.session_id == session.id,
            ParentNotification.student_id == student.id,
            ParentNotification.is_cancelled == False
        ).first()

        if existing_notif:
            results["duplicates_prevented"] += 1
            results["details"].append({
                "student_id": student.id,
                "student_name": student.name,
                "status": "ABSENT",
                "action": "DUPLICATE_PREVENTED",
                "existing_notification_id": existing_notif.id
            })
            continue

        # Message format including student name, class, subject, date, and attendance status
        student_msg = (
            f"Dear {student.name}, AttendX AI Notice: "
            f"Class: {class_code}, Subject: {session.subject_name}, Date: {session_date_str}, "
            f"Status: ABSENT. "
            f"Agar attendance galat hai, to apne teacher ({teacher_label}) se contact karein."
        )

        # 1. Student Notification Dispatch
        student_phone = (student.phone or "").strip()
        s_dispatch = send_sms_notification(student_phone, student_msg)

        student_notif = ParentNotification(
            student_id=student.id,
            session_id=session.id,
            recipient_type="STUDENT",
            recipient_name=student.name,
            recipient_phone=student_phone or None,
            parent_name=student.parent_name or f"Guardian of {student.name}",
            parent_phone=student.parent_phone or student_phone or "NOT_REGISTERED",
            alert_type="UNEXCUSED_ABSENCE",
            channel="SMS",
            delivery_provider=s_dispatch["provider"],
            message=student_msg,
            attendance_rate="ABSENT",
            status=s_dispatch["status"],
            error_message=s_dispatch.get("error"),
            is_cancelled=False,
            retry_count=0,
            sent_at=datetime.now(timezone.utc)
        )
        db.add(student_notif)
        results["student_notifications_sent"] += 1

        # 2. Parent Notification Dispatch
        parent_phone = (student.parent_phone or "").strip()
        parent_enabled = bool(student.parent_notifications_enabled if student.parent_notifications_enabled is not None else True)
        p_status = "NOT_CONFIGURED"

        if parent_phone and parent_enabled:
            parent_msg = (
                f"Dear Parent/Guardian of {student.name} ({student.roll_number or 'N/A'}), AttendX AI Notice: "
                f"Class: {class_code}, Subject: {session.subject_name}, Date: {session_date_str}. "
                f"Aapka ward aaj class mein उपस्थित nahi tha. Status: ABSENT. Faculty: {teacher_label}."
            )
            p_dispatch = send_sms_notification(parent_phone, parent_msg)

            parent_notif = ParentNotification(
                student_id=student.id,
                session_id=session.id,
                recipient_type="PARENT",
                recipient_name=student.parent_name or f"Parent of {student.name}",
                recipient_phone=parent_phone,
                parent_name=student.parent_name or f"Parent of {student.name}",
                parent_phone=parent_phone,
                alert_type="UNEXCUSED_ABSENCE",
                channel="SMS",
                delivery_provider=p_dispatch["provider"],
                message=parent_msg,
                attendance_rate="ABSENT",
                status=p_dispatch["status"],
                error_message=p_dispatch.get("error"),
                is_cancelled=False,
                retry_count=0,
                sent_at=datetime.now(timezone.utc)
            )
            db.add(parent_notif)
            results["parent_notifications_sent"] += 1
            p_status = p_dispatch["status"]
        elif not parent_phone:
            p_status = "MISSING_PHONE"
        else:
            p_status = "DISABLED_BY_USER"

        results["details"].append({
            "student_id": student.id,
            "student_name": student.name,
            "roll_number": student.roll_number,
            "class_code": class_code,
            "student_phone_masked": mask_phone_number(student.phone),
            "student_sms_status": s_dispatch["status"],
            "student_sms_provider": s_dispatch["provider"],
            "parent_name": student.parent_name,
            "parent_phone_masked": mask_phone_number(student.parent_phone),
            "parent_sms_status": p_status,
            "action": "ABSENT_ALERT_DISPATCHED"
        })

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"[Notification] Commit failed during absentee reconciliation: {e}")
        raise e

    return results


def sync_attendance_correction(
    db: Session,
    session_id: int,
    student_id: int,
    new_status: AttendanceStatus,
    updated_by_name: str = "Instructor"
) -> int:
    """
    When attendance status is manually or biometrically updated to PRESENT:
    Automatically updates prior absent notifications for this session/student
    to status 'CORRECTED_TO_PRESENT' with is_cancelled=True.
    """
    if new_status != AttendanceStatus.PRESENT:
        return 0

    records = db.query(ParentNotification).filter(
        ParentNotification.session_id == session_id,
        ParentNotification.student_id == student_id,
        ParentNotification.alert_type == "UNEXCUSED_ABSENCE",
        ParentNotification.is_cancelled == False
    ).all()

    now_iso = datetime.now(timezone.utc).isoformat()
    updated_count = 0
    for r in records:
        r.status = "CORRECTED_TO_PRESENT"
        r.is_cancelled = True
        correction_note = f"[CORRECTED] Status updated to PRESENT by {updated_by_name} at {now_iso}."
        r.error_message = f"{r.error_message} | {correction_note}" if r.error_message else correction_note
        updated_count += 1

    if updated_count > 0:
        db.commit()
        logger.info(f"[Notification] Corrected {updated_count} absent alert(s) for student {student_id} in session {session_id}.")

    return updated_count


def retry_sms_notification(db: Session, notification_id: int) -> Dict[str, Any]:
    """
    Retries an existing notification dispatch.
    """
    notif = db.query(ParentNotification).filter(ParentNotification.id == notification_id).first()
    if not notif:
        return {"success": False, "error": f"Notification {notification_id} not found."}

    phone = notif.recipient_phone or notif.parent_phone
    if not phone or phone == "NOT_REGISTERED":
        notif.status = "MISSING_PHONE"
        notif.error_message = "Recipient phone number is missing."
        db.commit()
        return {
            "success": False,
            "status": "MISSING_PHONE",
            "error": "No recipient phone number on record."
        }

    dispatch_res = send_sms_notification(phone, notif.message)
    notif.status = dispatch_res["status"]
    notif.delivery_provider = dispatch_res["provider"]
    notif.error_message = dispatch_res.get("error")
    notif.retry_count = (notif.retry_count or 0) + 1
    notif.sent_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(notif)

    return {
        "success": True,
        "notification_id": notif.id,
        "recipient_type": notif.recipient_type,
        "status": notif.status,
        "provider": notif.delivery_provider,
        "retry_count": notif.retry_count,
        "sent_at": notif.sent_at.isoformat()
    }
