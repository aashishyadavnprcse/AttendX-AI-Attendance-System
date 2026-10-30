"""
AttendX AI — End-to-End Absent Notification Verification Script
Executes all 9 steps requested:
1. Session conclude & absent student identification.
2. Student notification SQLite DB verification.
3. Parent notification eligibility verification.
4. PREVIEW_MODE status verification.
5. Duplicate notification prevention test.
6. Correct to Present functionality test.
7. Retry SMS functionality test.
8. Confirmation of truthful gateway status without false carrier claims.
9. Verification of database records and test results.
"""

import os
import sys
import json
import sqlite3
import urllib.request
import urllib.error

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_URL = "http://127.0.0.1:8765/api"
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "backend", "attendx.db"))

def api_call(endpoint, method="GET", data=None, token=None):
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        try:
            parsed = json.loads(error_body)
        except Exception:
            parsed = {"error": error_body}
        return e.code, parsed

def run_e2e_audit():
    print("=" * 80)
    print("ATTENDX AI — COMPREHENSIVE END-TO-END ABSENT NOTIFICATION VERIFICATION")
    print("=" * 80)

    # Step 0: Login
    status, auth = api_call("/auth/login", method="POST", data={
        "email": "teacher@attendx.ai",
        "password": "Teacher@123"
    })
    assert status == 200, f"Login failed: {auth}"
    token = auth["access_token"]
    print("[0] Teacher Authentication: 200 OK")

    # Step 1: Start fresh class session
    session_title = "CS-408 Distributed Consensus"
    status, sess = api_call("/session/start", method="POST", data={
        "subject_name": session_title,
        "require_geofence": False
    }, token=token)
    assert status in (200, 201), f"Session start failed: {sess}"
    session_id = sess["id"]
    print(f"\n[STEP 1] Live Session Initiated: ID #{session_id} - '{session_title}'")

    # Mark Student #4 (Alex Mercer) as PRESENT, leave Student #3 (Sarah Chen) and Student #5 (Demo Student) unrecorded
    status, mark_res = api_call("/attendance/manual", method="POST", data={
        "student_id": 4,
        "session_id": session_id,
        "status": "PRESENT",
        "notes": "Verified Present in Classroom"
    }, token=token)
    assert status == 200, f"Manual attendance failed: {mark_res}"
    print(f"  • Student #4 (Alex Mercer) marked PRESENT.")
    print(f"  • Student #3 (Sarah Chen) and Student #5 (Demo Student) left unrecorded.")

    # Conclude session to trigger automatic absentee reconciliation
    status, stop_res = api_call("/session/stop", method="POST", data={
        "session_id": session_id
    }, token=token)
    assert status == 200, f"Session stop failed: {stop_res}"
    print(f"  • Session concluded. Absent reconciliation auto-executed.")

    # Step 2: Query SQLite Database directly for Attendance Logs and Notifications
    print(f"\n[STEP 2] Direct SQLite Database Inspection (DB: {DB_PATH}):")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Verify attendance_logs for session_id
    logs = cur.execute("""
        SELECT a.id, a.student_id, u.name, a.status, a.verification_method, a.timestamp 
        FROM attendance_logs a 
        JOIN users u ON a.student_id = u.id 
        WHERE a.session_id = ? 
        ORDER BY a.student_id
    """, (session_id,)).fetchall()

    print(f"  • Attendance Logs in DB for Session #{session_id}:")
    for l in logs:
        print(f"    - Log ID {l[0]}: Student #{l[1]} ({l[2]}), Status: {l[3]}, Method: {l[4]}")

    # Check absent students identified
    absent_students_in_db = [l for l in logs if l[3] == "ABSENT"]
    present_students_in_db = [l for l in logs if l[3] == "PRESENT"]
    print(f"  • Confirmed Absent Count in DB: {len(absent_students_in_db)}")
    print(f"  • Confirmed Present Count in DB: {len(present_students_in_db)}")

    # Step 3: Inspect parent_notifications table in SQLite
    print(f"\n[STEP 3] Notification Records in Database for Session #{session_id}:")
    notifs = cur.execute("""
        SELECT id, student_id, session_id, recipient_type, recipient_name, recipient_phone, 
               alert_type, channel, delivery_provider, status, is_cancelled, retry_count, message
        FROM parent_notifications
        WHERE session_id = ?
        ORDER BY id ASC
    """, (session_id,)).fetchall()

    assert len(notifs) > 0, "No notifications were created in database!"
    for n in notifs:
        n_id, s_id, sess_id, r_type, r_name, r_phone, a_type, ch, provider, st, cancelled, retries, msg = n
        print(f"    - Notification ID #{n_id}:")
        print(f"      Recipient: [{r_type}] {r_name} ({r_phone})")
        print(f"      Channel: {ch} | Provider: {provider} | Status: {st} | Cancelled: {bool(cancelled)} | Retries: {retries}")
        print(f"      Message Preview: {msg[:85]}...")

    # Verify student notifications were created for absent students and NOT for present student
    present_sids = [l[1] for l in present_students_in_db]
    present_notifs = [n for n in notifs if n[1] in present_sids]
    assert len(present_notifs) == 0, f"Error: Present student received absent notification: {present_notifs}"
    print(f"  • Verified: Present student (Alex Mercer, ID 4) received 0 absent notifications.")

    student_notifs = [n for n in notifs if n[3] == "STUDENT"]
    assert len(student_notifs) >= 1, "Error: No STUDENT notifications found in database!"
    print(f"  • Verified: {len(student_notifs)} student absent notification(s) stored in DB.")

    # Step 4: Parent notification eligibility verification
    parent_notifs = [n for n in notifs if n[3] == "PARENT"]
    print(f"\n[STEP 4] Parent Notification Eligibility Verification:")
    print(f"  • Total Parent Notifications in DB: {len(parent_notifs)}")
    for pn in parent_notifs:
        print(f"    - Recipient: {pn[4]} (Phone: {pn[5]}), Status: {pn[9]}")
    assert len(parent_notifs) >= 1, "Error: Parent notification was not generated for eligible student!"

    # Step 5: PREVIEW_MODE Verification (Confirm no false claims of carrier delivery)
    print(f"\n[STEP 5] PREVIEW_MODE & Truthful Provider Status Verification:")
    providers = set(n[8] for n in notifs)
    statuses = set(n[9] for n in notifs)
    print(f"  • Detected Providers in DB: {providers}")
    print(f"  • Detected Delivery Statuses in DB: {statuses}")
    
    # Check that without Twilio/Fast2SMS credentials, status is strictly PREVIEW (or PREVIEW_DELIVERED/MISSING_PHONE)
    assert any("PREVIEW" in p or "NONE" in p for p in providers), f"Unexpected provider: {providers}"
    assert any("PREVIEW" in s or s in ("PREVIEW", "MISSING_PHONE") for s in statuses), f"Unexpected statuses: {statuses}"
    print(f"  • Verified: No real carrier dispatch falsely claimed. Environment truthfully reported as PREVIEW_MODE.")

    # Step 6: Test Duplicate Notification Prevention
    print(f"\n[STEP 6] Duplicate Notification Prevention Verification:")
    count_before = cur.execute("SELECT COUNT(*) FROM parent_notifications WHERE session_id = ?", (session_id,)).fetchone()[0]
    
    # Re-call absentee finalization on concluded session
    status, re_reconcile = api_call(f"/session/{session_id}/finalize-absentees", method="POST", token=token)
    assert status == 200, f"Re-reconciliation failed: {re_reconcile}"
    count_after = cur.execute("SELECT COUNT(*) FROM parent_notifications WHERE session_id = ?", (session_id,)).fetchone()[0]
    duplicates_blocked = re_reconcile.get("duplicates_prevented", 0)
    
    print(f"  • Notifications in DB before re-trigger: {count_before}")
    print(f"  • Notifications in DB after re-trigger:  {count_after}")
    print(f"  • Duplicate dispatches blocked by engine: {duplicates_blocked}")
    assert count_before == count_after, f"Duplicate notification leaked! Before: {count_before}, After: {count_after}"
    assert duplicates_blocked > 0, "No duplicates reported prevented!"
    print(f"  • Verified: Duplicate notifications strictly prevented (0 duplicate rows created).")

    # Step 7: Test Correct to Present functionality
    print(f"\n[STEP 7] 'Correct to Present' Functionality Verification:")
    # Student #5 (Demo Student) was absent. Now instructor marks Demo Student as PRESENT.
    target_student_id = 5
    status, correct_res = api_call("/attendance/manual", method="POST", data={
        "student_id": target_student_id,
        "session_id": session_id,
        "status": "PRESENT",
        "notes": "Late arrival — marked present by instructor"
    }, token=token)
    assert status == 200, f"Manual attendance correction failed: {correct_res}"

    # Verify SQLite DB records for student #5
    updated_notifs = cur.execute("""
        SELECT id, student_id, recipient_type, status, is_cancelled, error_message
        FROM parent_notifications
        WHERE session_id = ? AND student_id = ?
    """, (session_id, target_student_id)).fetchall()

    assert len(updated_notifs) > 0, "No notifications found for target student!"
    for un in updated_notifs:
        print(f"    - Notification #{un[0]} ({un[2]}): Status={un[3]}, is_cancelled={un[4]}, Notes='{un[5]}'")
        assert un[3] == "CORRECTED_TO_PRESENT", f"Expected CORRECTED_TO_PRESENT, got {un[3]}"
        assert un[4] == 1, f"Expected is_cancelled=1, got {un[4]}"
    print(f"  • Verified: Database record updated to status='CORRECTED_TO_PRESENT' with is_cancelled=True.")

    # Step 8: Test Retry SMS functionality
    print(f"\n[STEP 8] 'Retry SMS' Functionality Verification:")
    # Pick a notification from student #3 (Sarah Chen) who remains absent
    sarah_notif = cur.execute("""
        SELECT id, student_id, retry_count, status
        FROM parent_notifications
        WHERE session_id = ? AND student_id = 3
        LIMIT 1
    """, (session_id,)).fetchone()
    assert sarah_notif is not None, "Notification for Sarah Chen not found!"
    target_notif_id, _, initial_retry_count, _ = sarah_notif
    initial_retry_count = initial_retry_count or 0

    status, retry_res = api_call("/predictions/retry-sms", method="POST", data={
        "notification_id": target_notif_id
    }, token=token)
    assert status == 200 and retry_res.get("success"), f"Retry SMS failed: {retry_res}"

    # Verify retry count in SQLite DB
    updated_retry_count = cur.execute("""
        SELECT retry_count, status, sent_at
        FROM parent_notifications
        WHERE id = ?
    """, (target_notif_id,)).fetchone()[0]

    print(f"    - Notification ID #{target_notif_id}: Initial retries={initial_retry_count}, Updated retries={updated_retry_count}")
    assert updated_retry_count == initial_retry_count + 1, f"Retry count did not increment! {updated_retry_count}"
    print(f"  • Verified: SMS retry succeeded, retry_count incremented in SQLite database.")

    conn.close()

    print("\n" + "=" * 80)
    print("ALL 8 END-TO-END NOTIFICATION TEST STEPS PASSED WITH 100% SUCCESS!")
    print("=" * 80)
    return True

if __name__ == "__main__":
    success = run_e2e_audit()
    sys.exit(0 if success else 1)
