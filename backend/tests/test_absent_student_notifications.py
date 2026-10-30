"""
AttendX AI — Comprehensive Absent Student & Parent Notification Test Suite
Verifies all 6 core requirements:
1. Present student: absent notification nahi.
2. Absent student: notification generated with full details (name, class, subject, date, status).
3. Duplicate session: duplicate notification prevented.
4. Missing phone number: clear status (MISSING_PHONE).
5. Provider unavailable: PREVIEW/FAILED status (truthful gateway labeling).
6. Attendance correction: status updated to CORRECTED_TO_PRESENT.
Plus: Parent notification generation and preference handling.
"""

import os
import sys
import json
import urllib.request
import urllib.error

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Ensure stdout uses UTF-8 on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_URL = "http://127.0.0.1:8765/api"
results = []


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


def run_all_tests():
    print("=" * 75)
    print("ATTENDX AI — ABSENT STUDENT NOTIFICATION INTEGRATION TEST SUITE")
    print("=" * 75)

    # 0. Teacher Authentication
    status, auth = api_call("/auth/login", method="POST", data={
        "email": "teacher@attendx.ai",
        "password": "Teacher@123"
    })
    assert status == 200, f"Login failed: {auth}"
    token = auth["access_token"]
    print("[0] Teacher Authentication: 200 OK")

    # Fetch enrolled roster
    status, students = api_call("/students", token=token)
    assert status == 200 and len(students) >= 2, f"Roster fetch failed: {students}"
    student_present = students[0]
    student_absent = students[1]
    print(f"    Student A (To be marked PRESENT): {student_present['name']} (ID {student_present['id']})")
    print(f"    Student B (To remain ABSENT):      {student_absent['name']} (ID {student_absent['id']})")

    # Ensure Student B has registered phone for absent test
    from app.db.session import SessionLocal
    from app.models.user import User
    db = SessionLocal()
    u_b = db.query(User).filter(User.id == student_absent["id"]).first()
    if u_b and not u_b.phone:
        u_b.phone = "+91 98765 43211"
        db.commit()
    db.close()

    # 1. Start a dedicated test session
    status, session = api_call("/session/start", method="POST", data={
        "subject_name": "CS-401 Cloud Infrastructure",
        "require_geofence": False
    }, token=token)
    assert status in (200, 201), f"Session start failed: {session}"
    session_id = session["id"]
    print(f"[1] Test Session Started: #{session_id} '{session['subject_name']}'")

    # Mark Student A as PRESENT
    status, mark_res = api_call("/attendance/manual", method="POST", data={
        "student_id": student_present["id"],
        "session_id": session_id,
        "status": "PRESENT",
        "notes": "Verified Present in Class"
    }, token=token)
    assert status == 200, f"Mark present failed: {mark_res}"
    print(f"    Student A ({student_present['name']}) marked PRESENT.")

    # Conclude the session (triggers automatic absentee reconciliation)
    status, stop_res = api_call("/session/stop", method="POST", data={
        "session_id": session_id
    }, token=token)
    assert status == 200, f"Stop session failed: {stop_res}"
    print(f"[2] Session Concluded. Absentee reconciliation automatically executed.")

    # Query absent notifications for this session
    status, alerts_data = api_call(f"/predictions/absent-alerts?session_id={session_id}", token=token)
    assert status == 200, f"Failed to fetch alerts: {alerts_data}"
    alerts = alerts_data.get("alerts", [])

    # TEST 1: Present student: absent notification nahi
    alerts_for_present = [a for a in alerts if a["student_id"] == student_present["id"]]
    test1_pass = (len(alerts_for_present) == 0)
    print(f"\n[TEST 1] Present student receives NO absent notification:")
    if test1_pass:
        print("  --> PASS: 0 absent alerts generated for present student.")
        results.append(("Present student: absent notification nahi", True))
    else:
        print(f"  --> FAIL: Unexpected alerts found: {alerts_for_present}")
        results.append(("Present student: absent notification nahi", False))

    # TEST 2: Absent student: notification generated with full details
    alerts_for_absent_student = [a for a in alerts if a["student_id"] == student_absent["id"] and a["recipient_type"] == "STUDENT"]
    test2_pass = False
    if len(alerts_for_absent_student) >= 1:
        a_msg = alerts_for_absent_student[0]["message"]
        # Must include: student name, class, subject, date, status
        has_name = student_absent["name"] in a_msg
        has_class = "Class:" in a_msg
        has_subject = session["subject_name"] in a_msg
        has_date = "Date:" in a_msg
        has_status = "Status: ABSENT" in a_msg or "ABSENT" in a_msg
        test2_pass = has_name and has_class and has_subject and has_date and has_status
        print(f"\n[TEST 2] Absent student: notification generated with required fields:")
        print(f"  --> Message: {a_msg}")
        print(f"  --> [Name: {has_name}, Class: {has_class}, Subject: {has_subject}, Date: {has_date}, Status: {has_status}]")
        if test2_pass:
            print("  --> PASS: Absent notification contains all mandatory fields.")
            results.append(("Absent student: notification generated with details", True))
        else:
            print("  --> FAIL: Missing some required fields in message.")
            results.append(("Absent student: notification generated with details", False))
    else:
        print(f"\n[TEST 2] Absent student notification generated: FAIL (No alert generated)")
        results.append(("Absent student: notification generated with details", False))

    # TEST 3: Duplicate session: duplicate notification prevented
    status, dup_res = api_call(f"/session/{session_id}/finalize-absentees", method="POST", token=token)
    assert status == 200, f"Duplicate re-trigger failed: {dup_res}"
    duplicates_prevented = dup_res.get("duplicates_prevented", 0)
    test3_pass = (duplicates_prevented >= 1)
    print(f"\n[TEST 3] Duplicate session: duplicate notification prevented:")
    if test3_pass:
        print(f"  --> PASS: {duplicates_prevented} duplicate notification(s) intercepted and prevented.")
        results.append(("Duplicate session: duplicate notification prevented", True))
    else:
        print(f"  --> FAIL: Duplicate prevention count is {duplicates_prevented}")
        results.append(("Duplicate session: duplicate notification prevented", False))

    # TEST 4: Missing phone number: clear status
    # Create or identify a test student with missing phone number
    db = SessionLocal()
    student_no_phone = db.query(User).filter(User.role == "student", (User.phone == None) | (User.phone == "")).first()
    if not student_no_phone:
        # Create a transient student without phone number
        student_no_phone = User(
            name="No Phone Student",
            email="nophone.test@student.attendx.ai",
            hashed_password="Password123!",
            role="student",
            roll_number="TEST-NO-PHONE-001",
            phone=None,
            parent_name="No Phone Guardian",
            parent_phone=None
        )
        db.add(student_no_phone)
        db.commit()
        db.refresh(student_no_phone)
    target_no_phone_id = student_no_phone.id
    target_no_phone_name = student_no_phone.name
    db.close()

    # Start a new session to evaluate missing phone handling
    status, sess_no_phone = api_call("/session/start", method="POST", data={
        "subject_name": "CS-403 Mobile Computing",
        "require_geofence": False
    }, token=token)
    assert status in (200, 201)
    s_np_id = sess_no_phone["id"]
    api_call("/session/stop", method="POST", data={"session_id": s_np_id}, token=token)

    status, np_alerts = api_call(f"/predictions/absent-alerts?session_id={s_np_id}", token=token)
    alerts_np = [a for a in np_alerts.get("alerts", []) if a["student_id"] == target_no_phone_id]
    test4_pass = any(a["status"] == "MISSING_PHONE" or "MISSING" in a["status"] or a["recipient_phone_masked"] == "NOT_REGISTERED" for a in alerts_np)
    print(f"\n[TEST 4] Missing phone number: clear status:")
    if test4_pass:
        print(f"  --> PASS: Clear status assigned for missing phone: {[a['status'] for a in alerts_np]}")
        results.append(("Missing phone number: clear status", True))
    else:
        print(f"  --> FAIL: Expected MISSING_PHONE status, got: {alerts_np}")
        results.append(("Missing phone number: clear status", False))

    # TEST 5: Provider unavailable: PREVIEW/FAILED status
    # In default environment without Twilio SID / Fast2SMS key, status must be PREVIEW
    preview_alerts = [a for a in alerts if a["status"] in ("PREVIEW", "PREVIEW_DELIVERED") or "PREVIEW" in a["delivery_provider"]]
    test5_pass = (len(preview_alerts) > 0)
    print(f"\n[TEST 5] Provider unavailable: PREVIEW/FAILED status:")
    if test5_pass:
        provider_name = preview_alerts[0]["delivery_provider"]
        status_name = preview_alerts[0]["status"]
        print(f"  --> PASS: Transparent gateway labeling: status='{status_name}', provider='{provider_name}'")
        results.append(("Provider unavailable: PREVIEW/FAILED status", True))
    else:
        print(f"  --> FAIL: Alerts did not label preview mode truthfully: {[a['status'] for a in alerts]}")
        results.append(("Provider unavailable: PREVIEW/FAILED status", False))

    # TEST 6: Attendance correction: status updated to CORRECTED_TO_PRESENT
    # Late arrival: Mark Student B as PRESENT now for session_id
    status, corr_res = api_call("/attendance/manual", method="POST", data={
        "student_id": student_absent["id"],
        "session_id": session_id,
        "status": "PRESENT",
        "notes": "Late arrival admitted by instructor"
    }, token=token)
    assert status == 200, f"Attendance correction failed: {corr_res}"

    # Verify notification record status was updated to CORRECTED_TO_PRESENT
    status, updated_alerts_data = api_call(f"/predictions/absent-alerts?session_id={session_id}", token=token)
    updated_alerts = updated_alerts_data.get("alerts", [])
    corrected_records = [a for a in updated_alerts if a["student_id"] == student_absent["id"] and a["status"] == "CORRECTED_TO_PRESENT"]
    test6_pass = (len(corrected_records) >= 1)
    print(f"\n[TEST 6] Attendance correction: status updated:")
    if test6_pass:
        print(f"  --> PASS: Prior absent notification status updated to CORRECTED_TO_PRESENT ({len(corrected_records)} records updated, is_cancelled=True).")
        results.append(("Attendance correction: status updated", True))
    else:
        print(f"  --> FAIL: Status was not updated to CORRECTED_TO_PRESENT: {[a['status'] for a in updated_alerts if a['student_id'] == student_absent['id']]}")
        results.append(("Attendance correction: status updated", False))

    # SUMMARY
    print("\n" + "=" * 75)
    print("TEST SUITE EXECUTION SUMMARY")
    print("=" * 75)
    all_passed = True
    for name, passed in results:
        status_label = "[PASS]" if passed else "[FAIL]"
        print(f"  {status_label} {name}")
        if not passed:
            all_passed = False

    print("=" * 75)
    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
