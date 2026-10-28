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
    # Enrolled Sarah Chen has embedding: [0.05 * (i % 7) for i in range(128)]
    sarah_vector = [0.05 * (i % 7) for i in range(128)]
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

    print("\n==================================================================")
    print(" ALL BACKEND API ENDPOINTS FOR DASHBOARD VALIDATED SUCCESSFULLY! ")
    print("==================================================================")


if __name__ == "__main__":
    test_api_suite()
