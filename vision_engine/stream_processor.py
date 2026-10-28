"""
AttendX Vision Engine — Real-time Video Stream Processor
Renders the AttendX Cyberpunk HUD (Neon Cyan #06B6D4, Emerald #10B981, Rose #F43F5E)
over live camera feed with high-performance biometric telemetry.
"""

import sys
import time
from typing import Optional, Union
import cv2
import numpy as np

from vision_engine.service import AttendXVisionService

# BGR color palette matching the AttendX Design System:
COLOR_CYAN = (212, 182, 6)       # #06B6D4 Primary Accent
COLOR_EMERALD = (129, 185, 16)   # #10B981 Verified Present
COLOR_ROSE = (94, 63, 244)       # #F43F5E Spoof / Danger
COLOR_AMBER = (11, 158, 245)     # #F59E0B Warning / Unknown
COLOR_DARK_BG = (25, 15, 11)     # #0B0F19 Dark Canvas
COLOR_TEXT = (246, 244, 243)     # Off-white text


def draw_hud_corners(img: np.ndarray, bbox: list, color: tuple, length: int = 18, thickness: int = 2):
    """Draws sleek sci-fi corner bracket accents on the bounding box."""
    x1, y1, x2, y2 = bbox
    # Top-Left
    cv2.line(img, (x1, y1), (x1 + length, y1), color, thickness)
    cv2.line(img, (x1, y1), (x1, y1 + length), color, thickness)
    # Top-Right
    cv2.line(img, (x2, y1), (x2 - length, y1), color, thickness)
    cv2.line(img, (x2, y1), (x2, y1 + length), color, thickness)
    # Bottom-Left
    cv2.line(img, (x1, y2), (x1 + length, y2), color, thickness)
    cv2.line(img, (x1, y2), (x1, y2 - length), color, thickness)
    # Bottom-Right
    cv2.line(img, (x2, y2), (x2 - length, y2), color, thickness)
    cv2.line(img, (x2, y2), (x2, y2 - length), color, thickness)


def draw_scan_laser(img: np.ndarray, bbox: list, scan_phase: float):
    """Draws dynamic neon cyan laser scan sweep."""
    x1, y1, x2, y2 = bbox
    box_height = max(1, y2 - y1)
    laser_y = int(y1 + ((np.sin(scan_phase) + 1.0) / 2.0) * box_height)

    # Glow line
    cv2.line(img, (x1, laser_y), (x2, laser_y), COLOR_CYAN, 2)
    # Core highlight
    cv2.line(img, (x1, laser_y), (x2, laser_y), (255, 255, 255), 1)


def render_attendx_hud(frame: np.ndarray, result: dict, scan_phase: float, fps: float):
    """Renders the AttendX Vision HUD overlay on the video frame."""
    h, w, _ = frame.shape
    status = result.get("status", "UNKNOWN")
    student_id = result.get("student_id")
    confidence = result.get("confidence_score", 0.0)
    latency_ms = result.get("latency_ms", 0.0)
    liveness = result.get("liveness", {})
    bbox = result.get("bbox")

    # Select status color
    if status == "SUCCESS":
        status_color = COLOR_EMERALD
        status_badge = f"VERIFIED: {student_id} ({confidence * 100:.1f}%)"
    elif status == "SPOOF_DETECTED":
        status_color = COLOR_ROSE
        reasons = liveness.get("reasons", ["Spoof replay detected"])
        reason_txt = reasons[0] if reasons else "Attack detected"
        status_badge = f"SPOOF ALERT: {reason_txt}"
    else:
        status_color = COLOR_AMBER
        status_badge = "SCANNING / UNKNOWN IDENTITY"

    # 1. Top Telemetry Header Bar
    cv2.rectangle(frame, (0, 0), (w, 42), COLOR_DARK_BG, -1)
    cv2.line(frame, (0, 42), (w, 42), (60, 40, 30), 1)
    cv2.putText(frame, "AttendX AI VISION ENGINE v1.0", (16, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_CYAN, 2)
    cv2.putText(frame, f"FPS: {fps:.1f} | Latency: {latency_ms:.1f}ms", (w - 240, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)

    # 2. Face Bounding Box & HUD Elements
    if bbox:
        x1, y1, x2, y2 = bbox
        # Subtle bounding box
        cv2.rectangle(frame, (x1, y1), (x2, y2), status_color, 1)
        draw_hud_corners(frame, bbox, status_color, length=20, thickness=2)

        # Laser scan if in progress
        if status != "SPOOF_DETECTED":
            draw_scan_laser(frame, bbox, scan_phase)

        # Bottom Status Tag
        tag_y = min(h - 10, y2 + 25)
        cv2.rectangle(frame, (x1, y2 + 4), (x2, tag_y), COLOR_DARK_BG, -1)
        cv2.rectangle(frame, (x1, y2 + 4), (x2, tag_y), status_color, 1)
        cv2.putText(frame, status_badge, (x1 + 6, tag_y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.42, COLOR_TEXT, 1)

    # 3. Bottom Left Telemetry Stats
    ear_val = liveness.get("ear_avg", 0.0)
    tex_val = liveness.get("texture_score", 0.0)
    ref_val = liveness.get("reflection_score", 0.0)
    blinks = liveness.get("blink_count", 0)

    hud_y = h - 60
    cv2.putText(frame, f"EAR: {ear_val:.3f} | Blinks: {blinks}", (16, hud_y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
    cv2.putText(frame, f"Texture: {tex_val:.2f} | Anti-Reflection: {ref_val:.2f}", (16, hud_y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)


def run_stream_processor(
    source: Union[int, str] = 0,
    similarity_threshold: float = 0.68,
    require_blink: bool = False,
):
    """
    Starts video capture stream and processes frames in real-time.
    :param source: Webcam index (0) or RTSP URL or video file path.
    """
    print(f"[AttendX] Initializing stream processor on source: {source}...")
    service = AttendXVisionService(
        similarity_threshold=similarity_threshold,
        require_blink=require_blink
    )

    # Pre-seed demo student embeddings for instant recognition testing
    # Sarah Chen demo vector
    sarah_vector = [0.08 * (i % 9) for i in range(128)]
    service.enroll_student("CS-2026-001 (Sarah Chen)", sarah_vector)

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"[AttendX Error] Cannot open video source: {source}")
        return

    # Set 720p HD resolution for crisp processing
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    scan_phase = 0.0
    prev_time = time.time()
    fps = 30.0

    print("[AttendX] Video feed live. Press 'q' or ESC in window to exit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[AttendX] End of video stream.")
            break

        # Flip horizontally for natural selfie-cam mirror effect if webcam
        if source == 0:
            frame = cv2.flip(frame, 1)

        # Process frame
        result = service.process_frame(frame)

        # Update FPS
        curr_time = time.time()
        fps = 0.9 * fps + 0.1 * (1.0 / max(1e-5, (curr_time - prev_time)))
        prev_time = curr_time

        scan_phase += 0.08

        # Render Futuristic HUD
        render_attendx_hud(frame, result, scan_phase, fps)

        cv2.imshow("AttendX — AI Biometric Vision Stream", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:  # 'q' or ESC
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    src = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 0
    run_stream_processor(source=src)
