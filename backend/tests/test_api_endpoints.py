"""
AttendX API Endpoint Verification Test Suite
Tests FastAPI endpoints:
1. GET /api/analytics/realtime
2. POST /api/attendance/verify (Biometric + Liveness + 20m Geofence)
3. GET /api/attendance/reports (Filters, Summary, Pagination)
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token

client = TestClient(app)


def test_api_suite():
    print("==================================================================")
    print(" AttendX FastAPI Backend & Dashboard API Suite Verification")
    print("==================================================================")

    # 1. Health Check
    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    print("[1] Health Check: 200 OK")

    # 2. Login as Teacher
    res_login = client.post("/api/auth/login", json={"email": "teacher@attendx.ai", "password": "Teacher@123"})
    assert res_login.status_code == 200, f"Login failed: {res_login.text}"
    token = res_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[2] Teacher Login: 200 OK (JWT Bearer Token Issued)")

    # 3. GET /api/analytics/realtime
    res_analytics = client.get("/api/analytics/realtime", headers=headers)
    assert res_analytics.status_code == 200, f"Realtime analytics failed: {res_analytics.text}"
    data_analytics = res_analytics.json()
    print(f"[3] GET /api/analytics/realtime: 200 OK")
    print(f"    • Total Students: {data_analytics['total_students']}")
    print(f"    • Present Count: {data_analytics['present_count']}")
    print(f"    • Attendance Rate: {data_analytics['attendance_rate']}%")
    print(f"    • Recent Logs Count: {len(data_analytics['recent_logs'])}")
    assert "total_students" in data_analytics
    assert "attendance_rate" in data_analytics
    assert "recent_logs" in data_analytics

    # 4. POST /api/attendance/verify
    # Retrieve Sarah Chen's enrolled biometric embedding vector from DB
    from app.db.session import SessionLocal
    from app.models.user import User
    db_session = SessionLocal()
    sarah = db_session.query(User).filter(User.id == 3).first()
    sarah_vector = sarah.embedding_vector if (sarah and sarah.embedding_vector) else [0.05 * (i % 7) for i in range(128)]
    db_session.close()
    verify_payload = {
        "session_id": 1,
        "student_id": 3,
        "embedding_vector": sarah_vector,
        "latitude": 37.77492, # Within 5 meters of classroom (37.7749, -122.4194)
        "longitude": -122.41941,
        "is_live": True,
        "liveness_score": 0.992,
        "verification_method": "FACE_BIOMETRIC_LIVENESS"
    }
    res_verify = client.post("/api/attendance/verify", json=verify_payload, headers=headers)
    assert res_verify.status_code == 200, f"Attendance verify failed: {res_verify.text}"
    data_verify = res_verify.json()
    print(f"[4] POST /api/attendance/verify: 200 OK")
    print(f"    • Status: {data_verify['status']}")
    print(f"    • Student Name: {data_verify['student_name']}")
    print(f"    • Distance Meters: {data_verify['distance_meters']}m")
    print(f"    • Message: {data_verify['message']}")
    assert data_verify["status"] == "PRESENT"
    assert data_verify["student_name"] == "Sarah Chen"
    assert data_verify["geofence_verified"] is True

    # 5. GET /api/attendance/reports
    res_reports = client.get("/api/attendance/reports?page=1&page_size=10", headers=headers)
    assert res_reports.status_code == 200, f"Attendance reports failed: {res_reports.text}"
    data_reports = res_reports.json()
    print(f"[5] GET /api/attendance/reports: 200 OK")
    print(f"    • Total Records: {data_reports['total_records']}")
    print(f"    • Summary Present: {data_reports['summary']['present_count']}")
    print(f"    • Summary Attendance Rate: {data_reports['summary']['attendance_rate']}%")
    print(f"    • Records in Page: {len(data_reports['records'])}")
    assert "summary" in data_reports
    assert "records" in data_reports
    assert len(data_reports["records"]) >= 1

    # 6. GET /api/students
    res_students = client.get("/api/students", headers=headers)
    assert res_students.status_code == 200, f"List students failed: {res_students.text}"
    students_list = res_students.json()
    print(f"[6] GET /api/students: 200 OK ({len(students_list)} students retrieved)")
    assert len(students_list) >= 2

    # 7 & 8. Attendance Manual Workflow & Duplicate Prevention Test
    manual_present = {
        "student_id": 4,
        "session_id": 1,
        "status": "PRESENT",
        "notes": "Verified present by instructor during roll call"
    }
    res_first = client.post("/api/attendance/manual", json=manual_present, headers=headers)
    if res_first.status_code == 200:
        print(f"[7] POST /api/attendance/manual: 200 OK (Marked Alex Mercer PRESENT)")
        # Test duplicate
        res_dup = client.post("/api/attendance/manual", json=manual_present, headers=headers)
        assert res_dup.status_code == 409, f"Expected 409 duplicate conflict, got: {res_dup.status_code}"
        print(f"[8] Duplicate Attendance Prevention: 409 Conflict properly triggered")
    elif res_first.status_code == 409:
        print(f"[7] Duplicate Attendance Prevention: 409 Conflict properly triggered ({res_first.json()['detail']})")
        # Test status update (e.g. to ABSENT and back to PRESENT)
        manual_absent = {"student_id": 4, "session_id": 1, "status": "ABSENT", "notes": "Updated to ABSENT"}
        res_update = client.post("/api/attendance/manual", json=manual_absent, headers=headers)
        assert res_update.status_code == 200
        print(f"[8] Attendance Status Update: 200 OK (Updated status to ABSENT)")
        # Switch back to PRESENT
        res_back = client.post("/api/attendance/manual", json=manual_present, headers=headers)
        assert res_back.status_code == 200
        print(f"    Restored Alex Mercer to PRESENT: 200 OK")

    # 9. GET /api/session/current & POST /api/session/toggle
    res_session = client.get("/api/session/current", headers=headers)
    assert res_session.status_code == 200
    print(f"[9] GET /api/session/current: 200 OK (Active: {res_session.json()['is_active']})")

    # 10. GET /api/settings
    res_settings = client.get("/api/settings", headers=headers)
    assert res_settings.status_code == 200
    print(f"[10] GET /api/settings: 200 OK (Geofence: {res_settings.json()['geofence_radius_meters']}m)")

    # 11. GET /api/analytics/weekly
    res_weekly = client.get("/api/analytics/weekly", headers=headers)
    assert res_weekly.status_code == 200
    weekly_data = res_weekly.json()
    print(f"[11] GET /api/analytics/weekly: 200 OK (History records: {weekly_data['total_records']})")
    assert "labels" in weekly_data
    assert "present" in weekly_data

    print("\n==================================================================")
    print(" ALL BACKEND API ENDPOINTS FOR DASHBOARD VALIDATED SUCCESSFULLY! ")
    print("==================================================================")


if __name__ == "__main__":
    test_api_suite()
