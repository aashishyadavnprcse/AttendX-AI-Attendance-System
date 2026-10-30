# -*- coding: utf-8 -*-
"""
Verification suite for all 7 advanced feature categories of AttendX AI:
1. Multi-Face Detection, Liveness, and Anti-Spoofing
2. Continuous Presence & Timeline Analytics
3. Geo-fencing & BLE Proximity Verification
4. Gait & Posture Research Module
5. Tamper-Evident SHA-256 Ledger & Blockchain Prototype
6. ESP32-CAM & RFID IoT Gateway
7. Predictive Attendance Analytics & Parent Alerts
"""

import os
import sys

# Ensure backend directory is in path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_tests():
    print("=" * 70)
    print(" AttendX Advanced Feature Categories — Automated Verification Suite")
    print("=" * 70)

    # 0. Authenticate
    login_res = client.post("/api/auth/login", json={"email": "teacher@attendx.ai", "password": "Teacher@123"})
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}
    print("[0] Authentication: 200 OK (Bearer token acquired)")

    # 1. Multi-Face Batch Analysis & Anti-Spoofing
    batch_payload = {
        "session_id": 1,
        "image_source": "WEBCAM_BROWSER",
        "detected_faces": [
            {
                "face_index": 0,
                "bounding_box": [100, 100, 220, 240],
                "liveness_score": 0.94,
                "is_live": True,
                "suggested_roll_number": "CS-2026-001"
            },
            {
                "face_index": 1,
                "bounding_box": [300, 100, 420, 240],
                "embedding_vector": [0.01] * 128,
                "liveness_score": 0.88,
                "is_live": True
            },
            {
                "face_index": 2,
                "bounding_box": [500, 100, 620, 240],
                "liveness_score": 0.32,
                "is_live": False
            }
        ]
    }
    res = client.post("/api/face-engine/analyze-batch", json=batch_payload, headers=auth_headers)
    assert res.status_code == 200, f"Face engine failed: {res.text}"
    face_data = res.json()
    assert face_data["total_faces_detected"] == 3
    assert face_data["verified_matches_count"] >= 1
    assert face_data["review_queue_count"] >= 1
    assert face_data["spoofs_intercepted"] >= 1
    print(f"[1] Multi-Face Detection & Liveness Engine: 200 OK (3 faces processed: {face_data['verified_matches_count']} verified, {face_data['review_queue_count']} review queue, {face_data['spoofs_intercepted']} spoof blocked)")

    # 2. Continuous Presence & Timeline Analytics
    res = client.get("/api/presence/session/1/timeline", headers=auth_headers)
    assert res.status_code == 200, f"Presence failed: {res.text}"
    presence_data = res.json()
    assert "students_presence" in presence_data
    assert "intervals_sampled" in presence_data
    print(f"[2] Continuous Presence Analytics: 200 OK ({len(presence_data['intervals_sampled'])} intervals sampled; Policy: {presence_data['transparency_rule'][:32]}...)")

    # 3. BLE Proximity & Perimeter
    ble_payload = {
        "session_id": 1,
        "measured_rssi": -65,
        "tx_power": -59,
        "beacon_uuid": "ATTENDX-LAB-C402-BEACON",
        "mobile_device_model": "Pixel 8 Pro (Simulated)",
        "is_simulated_signal": True
    }
    res = client.post("/api/proximity/verify-ble", json=ble_payload, headers=auth_headers)
    assert res.status_code == 200, f"BLE proximity failed: {res.text}"
    ble_data = res.json()
    assert ble_data["is_in_ble_perimeter"] is True
    print(f"[3] BLE Micro-Proximity: 200 OK (Estimated distance: {ble_data['estimated_distance_meters']}m, Status: {ble_data['status']})")

    res = client.get("/api/proximity/classroom-perimeter/1", headers=auth_headers)
    assert res.status_code == 200, f"Classroom perimeter failed: {res.text}"
    perimeter_data = res.json()
    assert "geofence" in perimeter_data
    print(f"[3b] Classroom Perimeter Anchor: 200 OK (Lat: {perimeter_data['geofence']['classroom_latitude']}, Lon: {perimeter_data['geofence']['classroom_longitude']}, Radius: {perimeter_data['geofence']['radius_meters']}m)")

    # 4. Gait & Posture Research Module
    res = client.get("/api/research/metrics-catalog", headers=auth_headers)
    assert res.status_code == 200, f"Gait catalog failed: {res.text}"
    catalog = res.json()
    assert len(catalog["features"]) >= 3
    print(f"[4] Gait & Posture Research Catalog: 200 OK ({len(catalog['features'])} metrics defined)")

    posture_payload = {
        "session_id": 1,
        "is_simulation": True
    }
    res = client.post("/api/research/posture-analysis", json=posture_payload, headers=auth_headers)
    assert res.status_code == 200, f"Posture analysis failed: {res.text}"
    posture_res = res.json()
    assert "metrics" in posture_res
    print(f"[4b] Posture Analysis: 200 OK (Classification: {posture_res['metrics']['ergonomic_classification']}, Torso tilt: {posture_res['metrics']['torso_vertical_tilt_degrees']} deg)")

    # 5. Tamper-Evident SHA-256 Ledger & Blockchain Anchor
    res = client.get("/api/audit/ledger", headers=auth_headers)
    assert res.status_code == 200, f"Audit ledger failed: {res.text}"
    ledger_data = res.json()
    assert ledger_data["total_blocks"] >= 1
    print(f"[5] Tamper-Evident Audit Ledger: 200 OK (Total blocks: {ledger_data['total_blocks']})")

    res = client.get("/api/audit/verify-integrity", headers=auth_headers)
    assert res.status_code == 200, f"Integrity check failed: {res.text}"
    integrity_data = res.json()
    assert integrity_data["is_valid"] is True, f"Ledger integrity check failed: {integrity_data.get('error')}"
    print(f"[5b] SHA-256 Cryptographic Chain Verification: 200 OK (Valid: {integrity_data['is_valid']}, {integrity_data['blocks_verified']} blocks verified)")

    # 6. ESP32-CAM & RFID IoT Gateway
    res = client.get("/api/iot/devices", headers=auth_headers)
    assert res.status_code == 200, f"IoT devices failed: {res.text}"
    devices_data = res.json()
    assert devices_data["total_registered_devices"] >= 2
    print(f"[6] IoT Edge Nodes Gateway: 200 OK ({devices_data['total_registered_devices']} devices provisioned)")

    esp_payload = {
        "device_id": "ESP32-CAM-01",
        "session_id": 1,
        "resolution": "VGA_640x480"
    }
    res = client.post("/api/iot/esp32-frame", json=esp_payload, headers=auth_headers)
    assert res.status_code == 200, f"ESP32 frame failed: {res.text}"
    print(f"[6b] ESP32-CAM Frame Telemetry: 200 OK (Status: {res.json()['status']})")

    # 7. Predictive Risk & Parent Notification
    res = client.get("/api/predictions/risk-summary", headers=auth_headers)
    assert res.status_code == 200, f"Risk summary failed: {res.text}"
    risk_data = res.json()
    assert "student_risks" in risk_data
    print(f"[7] Predictive Risk Engine: 200 OK (Evaluated: {risk_data['total_evaluated_students']} students)")

    alert_payload = {
        "student_id": 3,
        "channel": "SMS_MOCK",
        "custom_message": "AttendX Alert: Verification automated test"
    }
    res = client.post("/api/predictions/dispatch-alert", json=alert_payload, headers=auth_headers)
    assert res.status_code == 200, f"Dispatch alert failed: {res.text}"
    alert_res = res.json()
    assert alert_res["status"] in ["DELIVERED", "PREVIEW_DELIVERED", "PREVIEW", "SENT"]
    print(f"[7b] Parent Alert Dispatcher: 200 OK (Recipient: {alert_res['recipient_phone']}, Status: {alert_res['status']})")

    res = client.get("/api/predictions/history", headers=auth_headers)
    assert res.status_code == 200, f"History failed: {res.text}"
    print(f"[7c] Parent Alert Audit History: 200 OK ({res.json().get('total_logged', len(res.json().get('records', [])))} total notifications)")

    print("=" * 70)
    print(" ALL 7 ADVANCED FEATURE CATEGORIES VERIFIED AND PASSING!")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
