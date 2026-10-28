"""
AttendX Notification Service — Self-Contained Test Suite
Validates:
1. 3-day consecutive absence & bunk detection across distinct calendar dates.
2. Dynamic variable templating (Parent Name, Student Name, Subject, Date).
3. WhatsApp message formatting and mock dispatch.
4. Duplicate daily alert suppression.
"""

from datetime import datetime, timezone, timedelta
import sys
from pathlib import Path

# Force UTF-8 on Windows consoles to support WhatsApp alert emojis
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root and backend to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))
sys.path.append(str(Path(__file__).resolve().parent.parent / "backend"))

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.db.session import Base
    from app.models.user import User, UserRole
    from app.models.session import ClassSession
    from app.models.attendance import AttendanceLog, AttendanceStatus
    from app.core.security import get_password_hash
    from notification_service.absence_detector import ConsecutiveAbsenceDetector
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False

from notification_service.whatsapp_client import WhatsAppNotifier


def test_message_formatting_and_client():
    print("\n--- Testing WhatsApp Dynamic Message Formatting & Client ---")
    notifier = WhatsAppNotifier(provider="mock")

    student_name = "Alex Mercer"
    parent_name = "Robert Mercer"
    subject = "Neural Networks & Computer Vision"
    date_str = "2026-10-28"
    consecutive_days = 3

    msg = notifier.format_alert_message(
        parent_name=parent_name,
        student_name=student_name,
        subject=subject,
        date_str=date_str,
        consecutive_days=consecutive_days,
    )

    print("Formatted Alert Message:\n")
    print(msg)

    assert "Dear Robert Mercer," in msg
    assert "Alex Mercer" in msg
    assert "Neural Networks & Computer Vision" in msg
    assert "3 consecutive lecture days" in msg
    assert "2026-10-28" in msg

    # Test dispatch
    res = notifier.send_absence_alert(
        parent_phone="+14155558923",
        parent_name=parent_name,
        student_name=student_name,
        subject=subject,
        date_str=date_str,
        consecutive_days=consecutive_days,
    )
    assert res["success"] is True
    assert res["status"] == "delivered_mock"
    print("\n✅ Template formatting and sandbox dispatch verified successfully.")


def run_notification_tests():
    print("==================================================================")
    print(" AttendX Automated Notification Microservice Test Suite")
    print("==================================================================")

    test_message_formatting_and_client()

    if not HAS_SQLALCHEMY:
        print("\n[Notice] SQLAlchemy not installed in current Python env.")
        print("To run the full DB integration test, execute: pip install -r notification_service/requirements.txt")
        print("==================================================================")
        return

    # Use isolated in-memory or test SQLite database
    test_db_url = "sqlite:///./test_notifications.db"
    engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    SessionTest = sessionmaker(bind=engine)
    db = SessionTest()

    try:
        print("\n1. Seeding test student with parent contact details...")
        student = User(
            name="Alex Mercer",
            email="alex.test@attendx.ai",
            hashed_password=get_password_hash("Student@123"),
            role=UserRole.STUDENT,
            roll_number="CS-2026-002",
            parent_name="Robert Mercer",
            parent_phone="+14155558923",
        )
        teacher = User(
            name="Dr. Elena Rostova",
            email="teacher.test@attendx.ai",
            hashed_password=get_password_hash("Teacher@123"),
            role=UserRole.TEACHER,
        )
        db.add_all([student, teacher])
        db.commit()

        # Seed 3 distinct class sessions across 3 consecutive days
        print("2. Generating 3 consecutive absent / bunk attendance records across 3 days...")
        today = datetime.now(timezone.utc)
        day_dates = [today - timedelta(days=2), today - timedelta(days=1), today]

        for i, log_date in enumerate(day_dates):
            session_obj = ClassSession(
                teacher_id=teacher.id,
                subject_name="Neural Networks & Computer Vision",
                start_time=log_date,
                is_active=False,
            )
            db.add(session_obj)
            db.commit()

            # Mark Day 1 & Day 2 as ABSENT, Day 3 as BUNK_DETECTED midway
            status_val = AttendanceStatus.ABSENT
            notes_val = "Unexcused absence" if i < 2 else "BUNK_DETECTED: Vacated seat SEAT_A2 midway during lecture"

            log = AttendanceLog(
                student_id=student.id,
                session_id=session_obj.id,
                timestamp=log_date,
                status=status_val,
                confidence_score=0.0,
                verification_method="CCTV_YOLO_BUNK_TRACKER" if i == 2 else "FACIAL_SCANNER",
                notes=notes_val,
            )
            db.add(log)
            db.commit()

        # 3. Test Consecutive Absence Detection
        print("\n3. Testing ConsecutiveAbsenceDetector for 3-day threshold...")
        detector = ConsecutiveAbsenceDetector(db_url=test_db_url)
        flagged = detector.scan_for_consecutive_absences(threshold_days=3)

        print(f" -> Flagged count: {len(flagged)}")
        assert len(flagged) == 1, f"Expected 1 flagged student, got {len(flagged)}"

        record = flagged[0]
        print(f" -> Student: {record['student_name']}")
        print(f" -> Consecutive Missing Days: {record['consecutive_days']}")
        print(f" -> Most Recent Subject: {record['last_subject']}")
        print(f" -> Parent Phone: {record['parent_phone']}")

        assert record["student_name"] == "Alex Mercer"
        assert record["consecutive_days"] == 3
        assert record["last_subject"] == "Neural Networks & Computer Vision"
        assert record["parent_phone"] == "+14155558923"

        # 4. Test WhatsApp Dynamic Variable Templating
        print("\n4. Verifying WhatsApp Dynamic Variable Formatting...")
        notifier = WhatsAppNotifier(provider="mock")
        alert_text = notifier.format_alert_message(
            parent_name=record["parent_name"],
            student_name=record["student_name"],
            subject=record["last_subject"],
            date_str=record["last_absence_date"],
            consecutive_days=record["consecutive_days"],
        )

        assert "Dear Robert Mercer," in alert_text
        assert "Alex Mercer" in alert_text
        assert "Neural Networks & Computer Vision" in alert_text
        assert "3 consecutive lecture days" in alert_text
        print(" -> All dynamic variables (Parent, Student, Subject, Date, Days) correctly populated.")

        # 5. Test Mock Message Dispatch
        print("\n5. Testing WhatsApp Dispatch Routine...")
        result = notifier.send_absence_alert(
            parent_phone=record["parent_phone"],
            parent_name=record["parent_name"],
            student_name=record["student_name"],
            subject=record["last_subject"],
            date_str=record["last_absence_date"],
            consecutive_days=record["consecutive_days"],
        )
        assert result["success"] is True
        print(f" -> Dispatch status: {result['status']}")

        # 6. Test Daily Duplicate Alert Suppression
        print("\n6. Testing Duplicate Alert Suppression...")
        detector.mark_alert_sent(record["student_id"])
        second_scan = detector.scan_for_consecutive_absences(threshold_days=3)
        print(f" -> Second scan immediately after notification: {len(second_scan)} flagged.")
        assert len(second_scan) == 0, "Student should be suppressed from duplicate alerts today."

        print("\n==================================================================")
        print(" ALL NOTIFICATION MICROSERVICE TESTS PASSED WITH 100% SUCCESS! ")
        print("==================================================================")

    finally:
        db.close()
        # Clean up test DB file
        try:
            Path("test_notifications.db").unlink(missing_ok=True)
        except Exception:
            pass


if __name__ == "__main__":
    run_notification_tests()
