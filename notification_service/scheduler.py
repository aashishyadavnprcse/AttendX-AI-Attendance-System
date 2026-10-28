"""
AttendX Notification Service — APScheduler Daily Automation Job
Configures a cron job running daily after class hours (default: 17:00 / 5:00 PM)
to detect 3-day consecutive absences/bunks and trigger automated parent WhatsApp messages.
"""

from datetime import datetime, timezone

try:
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger
except ImportError:
    BlockingScheduler = None
    CronTrigger = None

from notification_service.config import settings
from notification_service.whatsapp_client import WhatsAppNotifier
from notification_service.absence_detector import ConsecutiveAbsenceDetector


def execute_daily_parent_alerts(dry_run: bool = False):
    """
    Core job routine:
    1. Scan database for students with 3+ consecutive unexcused absences / bunks.
    2. Format dynamic WhatsApp message with Student Name, Date, and Subject.
    3. Dispatch WhatsApp alert via Twilio / Meta Cloud API.
    4. Log audit records to prevent duplicate notification on the same day.
    """
    print(f"\n=======================================================")
    print(f" [AttendX Cron] Running Daily Absence Notification Job")
    print(f" Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f" Mode: {'DRY RUN (Preview Only)' if dry_run else 'LIVE DISPATCH'}")
    print(f"=======================================================")

    detector = ConsecutiveAbsenceDetector()
    notifier = WhatsAppNotifier()

    flagged_students = detector.scan_for_consecutive_absences(
        threshold_days=settings.CONSECUTIVE_ABSENCE_DAYS
    )

    print(f"[AttendX Cron] Scan complete. Found {len(flagged_students)} students meeting the {settings.CONSECUTIVE_ABSENCE_DAYS}-day absence threshold.\n")

    dispatched_count = 0

    for s in flagged_students:
        print(f"📌 Flagged: {s['student_name']} ({s['roll_number']})")
        print(f"   • Consecutive Days Absent: {s['consecutive_days']}")
        print(f"   • Most Recent Subject: {s['last_subject']}")
        print(f"   • Parent Recipient: {s['parent_name']} ({s['parent_phone']})")

        if dry_run:
            msg = notifier.format_alert_message(
                parent_name=s["parent_name"],
                student_name=s["student_name"],
                subject=s["last_subject"],
                date_str=s["last_absence_date"],
                consecutive_days=s["consecutive_days"],
            )
            print(f"   [Dry Run Preview]:\n{msg}\n")
            dispatched_count += 1
            continue

        result = notifier.send_absence_alert(
            parent_phone=s["parent_phone"],
            parent_name=s["parent_name"],
            student_name=s["student_name"],
            subject=s["last_subject"],
            date_str=s["last_absence_date"],
            consecutive_days=s["consecutive_days"],
        )

        if result.get("success"):
            dispatched_count += 1
            detector.mark_alert_sent(s["student_id"])
            print(f"   ✅ Alert successfully dispatched via {result.get('provider')}!\n")
        else:
            print(f"   ❌ Alert dispatch failed: {result.get('error')}\n")

    print(f"[AttendX Cron] Daily job finished. Processed {dispatched_count} parent notifications.")
    return dispatched_count


def start_scheduler():
    """Starts the APScheduler blocking daemon with daily cron trigger."""
    scheduler = BlockingScheduler()

    trigger = CronTrigger(
        hour=settings.DAILY_CRON_HOUR,
        minute=settings.DAILY_CRON_MINUTE,
        timezone="UTC",
    )

    scheduler.add_job(
        execute_daily_parent_alerts,
        trigger=trigger,
        id="daily_absence_notification_job",
        name="Daily Attendance & Bunk Notification Job",
        replace_existing=True,
    )

    print(f"[AttendX Scheduler] Initialized. Daily cron scheduled for {settings.DAILY_CRON_HOUR:02d}:{settings.DAILY_CRON_MINUTE:02d} UTC.")
    print("[AttendX Scheduler] Running blocking scheduler. Press Ctrl+C to terminate.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n[AttendX Scheduler] Scheduler shutdown requested. Exiting.")
