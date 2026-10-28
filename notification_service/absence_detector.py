"""
AttendX Notification Service — Consecutive Absence & Bunk Detector
Queries the database to identify students who have been marked 'ABSENT'
or 'BUNK_DETECTED' for 3 or more consecutive lecture dates.
"""

from datetime import datetime, timezone, date
from typing import List, Dict, Any, Optional

try:
    from sqlalchemy import create_engine, desc, func
    from sqlalchemy.orm import sessionmaker
    HAS_SQLALCHEMY = True
except ImportError:
    create_engine = None
    desc = None
    func = None
    sessionmaker = None
    HAS_SQLALCHEMY = False

from notification_service.config import settings

# Import DB Models directly from backend
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent / "backend"))

try:
    from app.models.user import User, UserRole
    from app.models.session import ClassSession
    from app.models.attendance import AttendanceLog, AttendanceStatus
except ImportError:
    User = None
    UserRole = None
    ClassSession = None
    AttendanceLog = None
    AttendanceStatus = None


class ConsecutiveAbsenceDetector:
    """
    Scans student attendance logs across lecture days to detect consecutive absences.
    """

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or settings.DATABASE_URL
        connect_args = {}
        if self.db_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}

        self.engine = create_engine(self.db_url, connect_args=connect_args)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def scan_for_consecutive_absences(
        self, threshold_days: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Scans all students and returns those missing for >= threshold_days consecutive sessions.
        """
        db = self.SessionLocal()
        flagged_students = []

        try:
            students = db.query(User).filter(User.role == UserRole.STUDENT).all()

            for student in students:
                # Must have parent phone on file to receive alert
                if not student.parent_phone:
                    continue

                # Query student's attendance records ordered chronologically descending
                records = (
                    db.query(AttendanceLog, ClassSession)
                    .join(ClassSession, AttendanceLog.session_id == ClassSession.id)
                    .filter(AttendanceLog.student_id == student.id)
                    .order_by(desc(AttendanceLog.timestamp))
                    .all()
                )

                if not records:
                    continue

                # Track distinct date streak
                consecutive_count = 0
                missing_dates = []
                last_subject = "General Class"
                streak_active = True

                seen_dates = set()

                for log, session in records:
                    record_date = log.timestamp.date()
                    if record_date in seen_dates:
                        continue  # Only evaluate latest record per calendar day
                    seen_dates.add(record_date)

                    # Check if absent or bunked
                    is_unexcused = (
                        log.status == AttendanceStatus.ABSENT
                        or (log.notes and "BUNK_DETECTED" in log.notes)
                    )

                    if is_unexcused:
                        consecutive_count += 1
                        missing_dates.append(record_date.strftime("%Y-%m-%d"))
                        if not last_subject or last_subject == "General Class":
                            last_subject = session.subject_name
                    else:
                        # Present streak resets counter
                        streak_active = False
                        break

                # If threshold met
                if consecutive_count >= threshold_days:
                    # Check if parent was already alerted today
                    today_utc = datetime.now(timezone.utc).date()
                    if student.last_parent_alert_at and student.last_parent_alert_at.date() == today_utc:
                        print(f"[Detector] Student #{student.id} ({student.name}) meets threshold ({consecutive_count} days), but parent was already alerted today.")
                        continue

                    flagged_students.append({
                        "student_id": student.id,
                        "student_name": student.name,
                        "roll_number": student.roll_number,
                        "parent_name": student.parent_name or "Parent/Guardian",
                        "parent_phone": student.parent_phone,
                        "consecutive_days": consecutive_count,
                        "last_subject": last_subject,
                        "missing_dates": missing_dates,
                        "last_absence_date": missing_dates[0] if missing_dates else str(today_utc),
                    })

        finally:
            db.close()

        return flagged_students

    def mark_alert_sent(self, student_id: int):
        """Updates last_parent_alert_at timestamp to avoid duplicate daily alerts."""
        db = self.SessionLocal()
        try:
            student = db.query(User).filter(User.id == student_id).first()
            if student:
                student.last_parent_alert_at = datetime.now(timezone.utc)
                db.commit()
        finally:
            db.close()
