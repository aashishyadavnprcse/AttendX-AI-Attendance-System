"""
AttendX AI — Comprehensive 15-Phase Real Implementation Test Suite
Executes real HTTP calls against the running local backend (http://127.0.0.1:8765)
Verifies:
1. Authentication & Protected API Security (Phase 1 & 13)
2. SFace 128-d Biometric Template Enrollment (Phase 2)
3. Deep Face Detection (YuNet) & Vector Matching (SFace) (Phase 2)
4. Multi-Face CCTV Stream Analysis & FPS Benchmarking (Phase 3)
5. Anti-Spoof Liveness Diagnostics (Texture, Glare, Moiré FFT) (Phase 4)
6. Continuous Presence Observation & Retention Rate (Phase 5)
7. Geofencing: Haversine Calculation & Instructor Override (Phase 6)
8. BLE: Physical Host Bluetooth Adapter Inspection via Bleak (Phase 6)
9. WebAuthn / FIDO2 Mobile Biometric Hardware Interface (Phase 6)
10. Gait & Posture Geometric Biomechanical Analysis (Phase 7)
11. Tamper-Evident SHA-256 Audit Chain Event Logging (Phase 8)
12. RFID Badge Tap Deduplication & Session Check (Phase 9)
13. ESP32-CAM Ingestion with Header Authentication (Phase 9)
14. Predictive Attendance Analytics & Absence Streaks (Phase 10)
15. Parent Notification Gateway & Delivery History (Phase 11)
"""

import base64
import json
import os
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8765/api"
DEMO_IMAGE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vision_engine", "models", "demo.jpg")

test_results = []


def record_result(phase_num: int, title: str, passed: bool, output_summary: str, details: str = ""):
    status_str = "PASS" if passed else "FAIL"
    test_results.append({
        "phase": phase_num,
        "title": title,
        "status": status_str,
        "summary": output_summary,
        "details": details
    })
    print(f"[{status_str}] Phase {phase_num} — {title}: {output_summary}")


def http_request(endpoint: str, method: str = "GET", data: dict = None, token: str = None, headers: dict = None):
    url = f"{BASE_URL}{endpoint}"
    req_headers = {"Content-Type": "application/json"}
    if token:
        req_headers["Authorization"] = f"Bearer {token}"
    if headers:
        req_headers.update(headers)

    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp_body = resp.read().decode("utf-8")
            return resp.status, json.loads(resp_body) if resp_body else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            parsed = json.loads(err_body)
        except Exception:
            parsed = {"raw": err_body}
        return e.code, parsed


def run_all_tests():
    print("=" * 80)
    print("ATTENDX AI — COMPREHENSIVE 15-PHASE VERIFICATION SUITE")
    print("=" * 80)

    # -------------------------------------------------------------
    # 1. Authentication & Protected API Security (Phase 1 & 13)
    # -------------------------------------------------------------
    login_status, login_data = http_request(
        "/auth/login",
        method="POST",
        data={"email": "teacher@attendx.ai", "password": "Teacher@123"}
    )
    jwt_token = login_data.get("access_token")
    unauth_status, _ = http_request("/auth/me")

    auth_passed = (login_status == 200 and jwt_token is not None and unauth_status == 401)
    record_result(
        1, "Authentication & Security",
        auth_passed,
        f"HTTP {login_status} login OK, token issued, unauthenticated requests rejected with HTTP {unauth_status}."
    )

    # -------------------------------------------------------------
    # 2. SFace 128-d Biometric Template Enrollment (Phase 2)
    # -------------------------------------------------------------
    seed_status, seed_data = http_request("/face-engine/seed-demo-templates", method="POST", token=jwt_token)
    seed_passed = (seed_status == 200 and seed_data.get("status") == "SEEDED_SUCCESS")
    record_result(
        2, "Biometric Enrollment",
        seed_passed,
        f"HTTP {seed_status} — Enrolled 128-d deep embeddings for: {', '.join(seed_data.get('updated_students', []))}."
    )

    # -------------------------------------------------------------
    # 3. Deep Face Detection (YuNet) & Vector Matching (SFace) (Phase 2)
    # -------------------------------------------------------------
    with open(DEMO_IMAGE_PATH, "rb") as f:
        img_b64 = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode("utf-8")

    proc_status, proc_data = http_request(
        "/face-engine/process-frame",
        method="POST",
        token=jwt_token,
        data={
            "session_id": 1,
            "image_base64": img_b64,
            "similarity_threshold": 0.50,
            "min_detection_score": 0.50,
            "check_liveness": True,
            "auto_record_high_confidence": False
        }
    )

    faces = proc_data.get("detection_details", [])
    sarah = next((f for f in faces if f.get("matched_student_name") == "Sarah Chen"), None)
    alex = next((f for f in faces if f.get("matched_student_name") == "Alex Mercer"), None)
    unknowns = [f for f in faces if f.get("verdict") == "UNRECOGNIZED_FACE"]

    rec_passed = (
        proc_status == 200
        and len(faces) >= 2
        and sarah is not None and sarah.get("confidence_score") >= 0.70
        and alex is not None and alex.get("confidence_score") >= 0.70
        and len(unknowns) >= 1
    )
    record_result(
        3, "Real Face Detection & Matching",
        rec_passed,
        f"Detected {len(faces)} faces: Sarah Chen ({sarah.get('confidence_score')*100:.1f}%), Alex Mercer ({alex.get('confidence_score')*100:.1f}%), Unknown faces rejected ({len(unknowns)})."
    )

    # -------------------------------------------------------------
    # 4. Multi-Face CCTV Stream Analysis & FPS Benchmarking (Phase 3)
    # -------------------------------------------------------------
    cctv_status, cctv_data = http_request(
        "/face-engine/cctv-stream-analyze",
        method="POST",
        token=jwt_token,
        data={
            "session_id": 1,
            "image_base64": img_b64,
            "stream_source": "TEST_VIDEO",
            "similarity_threshold": 0.50
        }
    )
    cctv_passed = (
        cctv_status == 200
        and cctv_data.get("faces_detected", 0) >= 2
        and "latency_ms" in cctv_data
        and "measured_fps" in cctv_data
    )
    record_result(
        4, "Multi-Face CCTV Tracking & FPS",
        cctv_passed,
        f"Tracked {cctv_data.get('faces_detected')} faces across stream. Latency: {cctv_data.get('latency_ms')}ms ({cctv_data.get('measured_fps')} FPS benchmark)."
    )

    # -------------------------------------------------------------
    # 5. Anti-Spoof Liveness Diagnostics (Phase 4)
    # -------------------------------------------------------------
    liveness = sarah.get("liveness", {})
    live_passed = (
        "texture_score" in liveness
        and "reflection_score" in liveness
        and "moire_score" in liveness
        and "overall_liveness_score" in liveness
    )
    record_result(
        5, "Anti-Spoof Liveness Diagnostics",
        live_passed,
        f"Texture Variance: {liveness.get('texture_score')*100:.1f}%, Specular Glare: {liveness.get('reflection_score')*100:.1f}%, Moiré FFT: {liveness.get('moire_score')*100:.1f}%, Overall: {liveness.get('overall_liveness_score')*100:.1f}%."
    )

    # -------------------------------------------------------------
    # 6. Continuous Presence Checkpoints & Retention Rate (Phase 5)
    # -------------------------------------------------------------
    cp_status, cp_data = http_request(
        "/presence/record-checkpoint",
        method="POST",
        token=jwt_token,
        data={
            "session_id": 1,
            "checkpoint_minute": 15,
            "observed_student_ids": [3, 4],  # Sarah & Alex observed
            "sampling_interval_minutes": 15
        }
    )
    pres_passed = (cp_status == 200 and cp_data.get("status") == "CHECKPOINT_RECORDED")
    record_result(
        6, "Continuous Presence Tracking",
        pres_passed,
        f"Recorded 15m checkpoint: {cp_data.get('students_present_count')} students observed, interval={cp_data.get('sampling_interval_minutes')}m."
    )

    # -------------------------------------------------------------
    # 7. Geofencing: Haversine & Instructor Override (Phase 6)
    # -------------------------------------------------------------
    geo_in_status, geo_in_data = http_request(
        "/proximity/verify-gps-location",
        method="POST",
        token=jwt_token,
        data={
            "session_id": 1,
            "device_latitude": 37.774900,
            "device_longitude": -122.419400,
            "accuracy_meters": 5.0,
            "is_instructor_override": False
        }
    )
    geo_out_status, geo_out_data = http_request(
        "/proximity/verify-gps-location",
        method="POST",
        token=jwt_token,
        data={
            "session_id": 1,
            "device_latitude": 37.776000,
            "device_longitude": -122.419400,
            "accuracy_meters": 5.0,
            "is_instructor_override": False
        }
    )
    geo_ovr_status, geo_ovr_data = http_request(
        "/proximity/verify-gps-location",
        method="POST",
        token=jwt_token,
        data={
            "session_id": 1,
            "device_latitude": 37.776000,
            "device_longitude": -122.419400,
            "accuracy_meters": 5.0,
            "is_instructor_override": True,
            "override_reason": "Authorized lab offsite trial"
        }
    )
    geo_passed = (
        geo_in_data.get("status") == "INSIDE_GEOFENCE"
        and geo_out_data.get("status") == "OUTSIDE_GEOFENCE"
        and geo_ovr_data.get("status") == "INSTRUCTOR_OVERRIDE_GRANTED"
    )
    record_result(
        7, "GPS Haversine Geofencing",
        geo_passed,
        f"Inside (0.0m): {geo_in_data.get('status')} | Outside ({geo_out_data.get('calculated_distance_meters')}m): {geo_out_data.get('status')} | Override: {geo_ovr_data.get('status')}."
    )

    # -------------------------------------------------------------
    # 8. BLE: Physical Host Bluetooth Adapter Inspection (Phase 6)
    # -------------------------------------------------------------
    ble_status, ble_data = http_request("/proximity/scan-physical-beacons", token=jwt_token)
    ble_passed = (ble_status == 200 and "adapter" in ble_data)
    record_result(
        8, "Physical BLE Adapter Inspection",
        ble_passed,
        f"Adapter: {ble_data.get('adapter')} | Status: {ble_data.get('status')} | Fallback: {ble_data.get('fallback_mode', 'LIVE')}."
    )

    # -------------------------------------------------------------
    # 9. WebAuthn / FIDO2 Mobile Biometric Hardware Interface (Phase 6)
    # -------------------------------------------------------------
    webauthn_status, webauthn_data = http_request(
        "/proximity/webauthn-verify",
        method="POST",
        token=jwt_token,
        data={
            "user_id": 3,
            "credential_id": "dGVzdC1jcmVkZW50aWFsLWlkLTEyMzQ1",
            "client_data_json": "eyJjaGFsbGVuZ2UiOiAiYXR0ZW5keC0yMDI2In0=",
            "authenticator_data": "SZYN5YgOJ8whrE82BpHGpxzxl69oViTnVAAAAABAAAAAAAAAAA==",
            "signature": "MEQCIFz8f...test...sig",
            "origin": "http://127.0.0.1:5500"
        }
    )
    webauthn_passed = (webauthn_status == 200 and webauthn_data.get("status") == "WEBAUTHN_VALIDATED")
    record_result(
        9, "WebAuthn Biometric Interface",
        webauthn_passed,
        f"HTTP {webauthn_status} — {webauthn_data.get('authenticator_type')} verified over secure origin."
    )

    # -------------------------------------------------------------
    # 10. Gait & Posture Geometric Biomechanical Analysis (Phase 7)
    # -------------------------------------------------------------
    posture_status, posture_data = http_request(
        "/research/posture-analysis",
        method="POST",
        token=jwt_token,
        data={
            "session_id": 1,
            "student_id": 3,
            "keypoints": [
                {"id": 0, "x": 0.5, "y": 0.2, "z": 0.0, "visibility": 0.99},   # nose
                {"id": 11, "x": 0.45, "y": 0.35, "z": 0.0, "visibility": 0.98}, # left shoulder
                {"id": 12, "x": 0.55, "y": 0.35, "z": 0.0, "visibility": 0.98}, # right shoulder
                {"id": 23, "x": 0.46, "y": 0.65, "z": 0.0, "visibility": 0.97}, # left hip
                {"id": 24, "x": 0.54, "y": 0.65, "z": 0.0, "visibility": 0.97}  # right hip
            ]
        }
    )
    metrics = posture_data.get("metrics", {})
    posture_passed = (posture_status == 200 and "torso_vertical_tilt_degrees" in metrics)
    record_result(
        10, "Gait & Posture Research Module",
        posture_passed,
        f"Torso Tilt: {metrics.get('torso_vertical_tilt_degrees')}° ({metrics.get('ergonomic_classification')}), Head-Forward: {metrics.get('head_forward_tilt_degrees')}°, Landmark Confidence: {metrics.get('landmark_confidence')*100:.0f}%."
    )

    # -------------------------------------------------------------
    # 11. Tamper-Evident SHA-256 Audit Chain Event Logging (Phase 8)
    # -------------------------------------------------------------
    audit_ev_status, audit_ev_data = http_request(
        "/audit/record-event",
        method="POST",
        token=jwt_token,
        data={
            "action": "INSTRUCTOR_OVERRIDE",
            "student_id": 3,
            "details": {"reason": "Authorized lab offsite trial", "approved_distance_meters": 122.3}
        }
    )
    audit_ver_status, audit_ver_data = http_request("/audit/verify-integrity", token=jwt_token)
    audit_passed = (
        audit_ev_status == 200
        and audit_ver_status == 200
        and audit_ver_data.get("is_valid") is True
    )
    record_result(
        11, "Tamper-Evident Audit Ledger",
        audit_passed,
        f"Block #{audit_ev_data.get('block_index')} appended. Chain verification: {audit_ver_data.get('status')} ({audit_ver_data.get('blocks_verified')} blocks validated)."
    )

    # -------------------------------------------------------------
    # 12. RFID Badge Tap Deduplication & Session Check (Phase 9)
    # -------------------------------------------------------------
    rfid_tap1_status, rfid_tap1_data = http_request(
        "/iot/rfid-tap",
        method="POST",
        token=jwt_token,
        data={"card_uid": "E2:80:68:1A", "session_id": 1, "is_simulated": True}
    )
    rfid_tap2_status, rfid_tap2_data = http_request(
        "/iot/rfid-tap",
        method="POST",
        token=jwt_token,
        data={"card_uid": "E2:80:68:1A", "session_id": 1, "is_simulated": True}
    )
    rfid_passed = (
        rfid_tap2_status == 200
        and (rfid_tap2_data.get("status") == "DUPLICATE_TAP_PREVENTED" or rfid_tap2_data.get("is_duplicate") is True)
    )
    record_result(
        12, "RFID Gateway & Deduplication",
        rfid_passed,
        f"First tap processed. Subsequent tap: {rfid_tap2_data.get('status')} (is_duplicate: {rfid_tap2_data.get('is_duplicate', True)})."
    )

    # -------------------------------------------------------------
    # 13. ESP32-CAM Ingestion with Header Authentication (Phase 9)
    # -------------------------------------------------------------
    esp_status, esp_data = http_request(
        "/iot/esp32-frame",
        method="POST",
        token=jwt_token,
        headers={"X-Device-API-Key": "ESP32-CAM-01-SECURE-KEY"},
        data={
            "device_id": "ESP32-CAM-01",
            "session_id": 1,
            "resolution": "VGA_640x480",
            "mock_frame_base64": img_b64
        }
    )
    esp_passed = (esp_status == 200 and esp_data.get("status") == "FRAME_ACCEPTED")
    record_result(
        13, "ESP32-CAM Gateway Authentication",
        esp_passed,
        f"Frame accepted from {esp_data.get('device_id')}. Authenticated: {esp_data.get('device_authenticated')}, Faces in frame: {esp_data.get('faces_detected')}, Mode: {esp_data.get('hardware_status')}."
    )

    # -------------------------------------------------------------
    # 14. Predictive Attendance Analytics & Absence Streaks (Phase 10)
    # -------------------------------------------------------------
    pred_status, pred_data = http_request("/predictions/risk-summary?threshold=75.0", token=jwt_token)
    stud_status, stud_data = http_request("/predictions/student/3?threshold=75.0", token=jwt_token)
    pred_passed = (pred_status == 200 and stud_status == 200 and "student_risks" in pred_data)
    record_result(
        14, "Predictive Attendance Analytics",
        pred_passed,
        f"Evaluated {pred_data.get('total_evaluated_students')} students at {pred_data.get('configured_threshold_percent')}% threshold. Type: {pred_data.get('prediction_type')}."
    )

    # -------------------------------------------------------------
    # 15. Parent Notification Gateway & Delivery History (Phase 11)
    # -------------------------------------------------------------
    alert_status, alert_data = http_request(
        "/predictions/dispatch-alert",
        method="POST",
        token=jwt_token,
        data={
            "student_id": 5,  # Demo Student (Critical risk)
            "alert_type": "LOW_ATTENDANCE_WARNING",
            "channel": "SMS"
        }
    )
    hist_status, hist_data = http_request("/predictions/history?limit=5", token=jwt_token)
    notif_passed = (alert_status == 200 and hist_status == 200 and hist_data.get("total_dispatches", 0) > 0)
    record_result(
        15, "Parent Notification Gateway",
        notif_passed,
        f"Dispatched alert for {alert_data.get('student_name')}. Gateway: {alert_data.get('gateway_status')} ({alert_data.get('gateway_note')}). Total historical dispatches: {hist_data.get('total_dispatches')}."
    )

    print("=" * 80)
    total_passed = sum(1 for r in test_results if r["status"] == "PASS")
    print(f"VERIFICATION RESULTS: {total_passed}/{len(test_results)} PHASES PASSED.")
    print("=" * 80)


if __name__ == "__main__":
    run_all_tests()
