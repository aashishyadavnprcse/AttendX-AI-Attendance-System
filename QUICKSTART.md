# AttendX — Quickstart & Execution Guide

Complete end-to-end guide to launching the **FastAPI Backend Server**, running the **OpenCV / MediaPipe CCTV Biometric Vision Agent**, and viewing the **Real-Time Telemetry Dashboard**.

---

## ⚡ 1. Launch the FastAPI Backend Server

The backend runs on **FastAPI** with native SQLite (`attendx.db`) and PostgreSQL compatibility, auto-seeding demo educator/student accounts and active class sessions upon launch.

```bash
# From workspace root
python -m uvicorn backend.server:app --reload --port 8000
```

- **Interactive Swagger API Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **System Health Check**: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)
- **Live Real-Time Analytics**: [http://127.0.0.1:8000/api/analytics/realtime](http://127.0.0.1:8000/api/analytics/realtime)

### Pre-Seeded Test Credentials:
- **Teacher**: `teacher@attendx.ai` (Password: `teacher123`)
  - Active Session: *Neural Networks & Computer Vision* (Room 402, 20m Geofence Anchor: `37.7749 N, -122.4194 W`)
- **Student 1**: `sarah.chen@student.attendx.ai` (Roll: `CS-2026-001`, 128-d biometric template enrolled)
- **Student 2**: `alex.mercer@student.attendx.ai` (Roll: `CS-2026-002`, 128-d biometric template enrolled)

---

## 👁️ 2. Run the CCTV Computer Vision Agent (`cctv_live_agent.py`)

The standalone Python agent connects **OpenCV** and **MediaPipe Face Mesh** directly to the running FastAPI server:
1. Calculates **Eye Aspect Ratio (EAR)** for 3D liveness blink detection.
2. Evaluates **specular glare** & **texture variance** to block mobile screen replay attacks.
3. Automatically hits `POST /api/attendance/verify` when an enrolled student's face is recognized.
4. Renders the Cyberpunk HUD overlay (Neon Cyan brackets, green verified box, red spoof alert).

```bash
# Mode A: Live webcam stream (Camera device 0)
python cctv_live_agent.py

# Mode B: Automated simulation mode (Runs immediately without needing a physical webcam)
python cctv_live_agent.py --simulate

# Mode C: Target an RTSP camera stream or video file
python cctv_live_agent.py --source rtsp://camera-ip:554/live
```

---

## 📊 3. View the Next.js / React Dashboard

Open the interactive dashboard preview in any browser:
👉 [dashboard-preview.html](file:///c:/Users/AASHISH%20KUMAR%20YADAV/OneDrive/Documents/smart%20attandence/dashboard-preview.html)

- **Live Metrics Grid**: Total Enrolled (1,443), Present (1,420), Spoofs Blocked (3), Attention (89.2%).
- **Split-Screen CCTV Stream**: Live animated scanning laser, green targeting box (Sarah Chen), red box (Spoof attack intercepted).
- **Auto-Syncing Activity Ticker**: Automatically prepends new verification events.
- **Interactive Charts**: 5-Day Weekly Attendance Bar Chart & MediaPipe Attention Breakdown Doughnut Chart.
