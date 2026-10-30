# AttendX AI — Complete Real Working Advanced Attendance System

An enterprise-grade, privacy-first, biometric smart attendance platform combining FastAPI, SQLite, real deep-learning face recognition (OpenCV YuNet + SFace ONNX), anti-spoof liveness verification, multi-face CCTV stream tracking, HTML5 browser geolocation geofencing, physical BLE adapter scanning, continuous presence checkpoints, tamper-evident SHA-256 audit ledger, IoT microcontrollers (ESP32-CAM & RFID), and explainable predictive risk notifications.

---

## 1. Project Overview & Architecture

AttendX AI is engineered for production readiness, hackathon demonstrations, and academic evaluation without fabricated claims or silent auto-attendance:

- **Real Deep-Learning Face Detection (YuNet ONNX)**: Runs OpenCV Zoo YuNet deep neural network natively to detect all human faces in video frames, computing bounding boxes and 5 facial landmarks (eyes, nose, mouth).
- **Deep Biometric Feature Recognition (SFace ONNX 128-d)**: Extracts 128-dimensional normalized facial embeddings and computes cosine similarity against enrolled database templates.
- **Two-Stage Instructor Confirmation Flow**: Face detection and identity matching are decoupled from recording. Ambiguous matches require explicit instructor confirmation before attendance is committed to SQLite.
- **Anti-Spoof Liveness Diagnostics**: Classical computer vision heuristics analyzing Laplacian micro-texture variance, HSV specular screen glare ratio, and 2D FFT periodic moiré harmonics.
- **Multi-Face CCTV Tracking & FPS Benchmarking**: Real-time centroid-based multi-face tracker assigning consistent track IDs across consecutive frames, reporting measured latency (ms) and processing FPS.
- **Real Browser Geolocation & Haversine Geofencing**: Acquires true device GPS coordinates via `navigator.geolocation`, enforces 20m classroom perimeter limits, and logs explicit instructor overrides in the audit trail.
- **Physical BLE Adapter Integration (Bleak / WinRT)**: Live Bluetooth LE discovery using host Windows Bluetooth hardware, gracefully detecting radio power state with calibrated simulation fallback.
- **Mobile Biometric WebAuthn / FIDO2 Interface**: Attestation framework for platform authenticators (Windows Hello, TouchID, Android Biometrics) over secure origins.
- **Continuous Classroom Presence Checkpoints**: Tracks student retention across scheduled intervals (15m, 30m, 45m) derived strictly from observation logs without psychoanalyzing emotion or attentiveness.
- **Tamper-Evident SHA-256 Cryptographic Ledger**: Block hash-chaining where each entry links to `previous_hash`, with instant tamper detection across attendance logs, overrides, and session changes.
- **IoT Edge Gateway (ESP32-CAM & RFID)**: Authenticated `X-Device-API-Key` headers, payload size validation, RFID UID deduplication, and transparent `HARDWARE_DISCONNECTED` labels when physical devices are detached.
- **Explainable Predictive Risk & Parent Alerts**: Computes course examination eligibility based on the empirical 75% cutoff and absence streaks, with SMS/SMTP gateway checks and delivery logs.

---

## 2. Subsystems & Implementation Classification

| Subsystem / Module | Status | Core Engine Files | Real Capabilities | Limitations / Disclosures |
| :--- | :--- | :--- | :--- | :--- |
| **1. AI Face Recognition** | **REAL WORKING** | `backend/app/services/cv_face_engine.py`, `backend/app/routers/face_engine.py` | OpenCV YuNet (ONNX) + SFace (ONNX), 128-d cosine matching, enrollment API. | Requires adequate lighting and unobstructed frontal face pose. |
| **2. Multi-Face CCTV Tracking** | **REAL WORKING** | `backend/app/services/cv_face_engine.py` | Centroid-based tracker, temporal track IDs, measured latency and FPS benchmarking. | Tested at ~15 FPS for 1–10 concurrent faces on CPU; server GPU recommended for 40+ faces. |
| **3. Anti-Spoof Liveness** | **REAL WORKING** | `vision_engine/anti_spoof/texture_analyzer.py` | Laplacian variance, HSV specular glare, 2D FFT moiré grid analysis. | **Heuristic Only**: Catches printed paper and glossy screens. Does not replace active 3D NIR structured-light sensors. |
| **4. Continuous Presence** | **REAL WORKING** | `backend/app/routers/presence.py` | Observation checkpoints, retention duration, attendance %, review flags. | Does not psychoanalyze facial expressions or infer distraction/sleeping. |
| **5. Geofencing** | **REAL WORKING** | `backend/app/services/geofence_validator.py`, `backend/app/routers/proximity.py` | `navigator.geolocation` acquisition, Haversine distance, override audit logging. | Accuracy depends on host device GPS / Wi-Fi positioning hardware. |
| **6. BLE Proximity** | **REAL WORKING** | `backend/app/routers/proximity.py` | Host WinRT Bluetooth scanning via `bleak`, radio status detection, Log-Distance Path Loss. | Physical scanning requires Bluetooth radio enabled in Windows Settings. |
| **7. Mobile Biometrics (FIDO2)** | **REAL WORKING** | `backend/app/routers/proximity.py` | WebAuthn credential verification, origin check, platform authenticator interface. | Requires secure origin (`https://` or `http://127.0.0.1`). |
| **8. Gait & Posture Research** | **REAL WORKING** | `backend/app/routers/gait_posture.py` | Biomechanical angle formulas, MediaPipe 33-point topology, missing landmark reporting. | Experimental research module. Not used for identity verification or punitive decisions. |
| **9. Tamper-Evident Ledger** | **REAL WORKING** | `backend/app/models/audit.py`, `backend/app/routers/audit.py` | Canonical SHA-256 block hash-chaining, tamper verification, event logging. | Ethereum receipts are local synthetic hex anchors (`0x...`), not live public RPC transactions. |
| **10. IoT Gateway (RFID / ESP32)** | **REAL WORKING** | `backend/app/routers/iot.py`, `backend/app/models/iot.py` | `X-Device-API-Key` auth, RFID deduplication, frame face extraction. | When microcontrollers are disconnected, labeled transparently as `HARDWARE_DISCONNECTED (MOCK)`. |
| **11. Predictive Analytics** | **REAL WORKING** | `backend/app/routers/predictions.py` | Configurable threshold cutoff, absence streaks, explainable formula calculation. | Empirical statistical indicator; does not claim black-box machine learning. |
| **12. Parent Notification Gateway** | **REAL WORKING** | `backend/app/routers/predictions.py` | Twilio / SMTP environment validation, recipient formatting, SQLite dispatch logs. | When no telecom provider keys are configured, operates in transparent preview mode. |

---

## 3. Technology Stack

- **Backend**: Python 3.14+, FastAPI, SQLAlchemy, SQLite (WAL mode), Pydantic v2, Passlib (Bcrypt), Python-Jose (JWT), Bleak (WinRT Bluetooth)
- **Computer Vision & AI**: OpenCV 5.0.0.93 DNN, YuNet Face Detector (`face_detection_yunet_2023mar.onnx`), SFace Face Recognizer (`face_recognition_sface_2021dec.onnx`)
- **Frontend**: HTML5, Tailwind CSS (Glassmorphism), Chart.js, WebRTC MediaStream, HTML5 Geolocation API, Vanilla ES6+
- **Security & Cryptography**: Canonical SHA-256 Hash Chained Ledger, Great-Circle Haversine Geodetics, Log-Distance Path Loss Model

---

## 4. Setup & Startup Commands

### Prerequisites
- Windows 10 or Windows 11
- Python 3.10+ installed and on `PATH`
- Modern browser (Google Chrome, Microsoft Edge, Brave, or Firefox)

### Terminal 1 — Start FastAPI Backend Server
```powershell
cd "C:\Users\AASHISH KUMAR YADAV\OneDrive\Documents\smart attandence\backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```
*Health Check:* `http://127.0.0.1:8765/api/health`  
*Swagger Documentation:* `http://127.0.0.1:8765/docs`

### Terminal 2 — Start Frontend Dashboard Web Server
```powershell
cd "C:\Users\AASHISH KUMAR YADAV\OneDrive\Documents\smart attandence"
python -m http.server 5500
```
*Frontend URL:* `http://127.0.0.1:5500/dashboard-preview.html`

### Terminal 3 — Execute 15-Phase Verification Test Suite
```powershell
cd "C:\Users\AASHISH KUMAR YADAV\OneDrive\Documents\smart attandence"
python test_real_implementation.py
```

---

## 5. Live Demonstration Workflow

### Step 1: Open Dashboard & Review Live Telemetry
- Open `http://127.0.0.1:5500/dashboard-preview.html`.
- Confirm backend connectivity status: `Backend: http://127.0.0.1:8765 (ONLINE)`.
- The live KPI cards display actual counts from `backend/attendx.db`.

### Step 2: Test Real Webcam Face Recognition
- Click **Start Camera** to activate the local webcam preview.
- Click **Seed Templates** to load reference embeddings for Sarah Chen and Alex Mercer.
- Click **Capture & Recognize Face**:
  - YuNet detects faces and renders real bounding boxes and 5 facial landmark dots on the video canvas overlay.
  - SFace extracts 128-d embeddings and matches against enrolled templates.
  - Displays match confidence %, texture variance score, reflection score, and moiré score.
- Click **Confirm Attendance**:
  - Records the verified log into SQLite `AttendanceLog`.
  - Updates the verification ticker in real time.
- Clicking confirm a second time demonstrates duplicate prevention enforcement.

### Step 3: Test Real Geolocation & Haversine Distance
- Navigate to **BLE & Geofence** (`nav-proximity`).
- Click **Acquire Real Device Location**:
  - Browser prompts for location permission (`navigator.geolocation`).
  - Displays real latitude, longitude, and accuracy reported by your device.
  - Computes exact Haversine distance from the classroom coordinates.
- Test the **Instructor Manual Override** checkbox to demonstrate authorized exception handling with audit trail logging.

### Step 4: Audit Ledger Verification
- Navigate to **Audit Ledger** (`nav-audit`).
- Click **Verify Cryptographic Chain**:
  - Evaluates SHA-256 hash-linking across every historical block.
  - Confirms zero database tampering or altered records.

### Step 5: Predictive Risk & Parent Alerts
- Navigate to **Risk & Parent Alerts** (`nav-predictions`).
- Review student risk tiers based on the empirical 75% exam cutoff.
- Click **Dispatch Parent Alert**:
  - Evaluates student attendance percentage.
  - Dispatches alert into SQLite `parent_notifications` table with gateway delivery status.

---

## 6. Automated Test Results (15/15 Passed)

```
================================================================================
ATTENDX AI — COMPREHENSIVE 15-PHASE VERIFICATION SUITE
================================================================================
[PASS] Phase 1 — Authentication & Security: HTTP 200 login OK, token issued, unauthenticated requests rejected with HTTP 401.
[PASS] Phase 2 — Biometric Enrollment: HTTP 200 — Enrolled 128-d deep embeddings for: Sarah Chen, Alex Mercer.
[PASS] Phase 3 — Real Face Detection & Matching: Detected 7 faces: Sarah Chen (100.0%), Alex Mercer (100.0%), Unknown faces rejected (3).
[PASS] Phase 4 — Multi-Face CCTV Tracking & FPS: Tracked 7 faces across stream. Latency: 63.99ms (15.6 FPS benchmark).
[PASS] Phase 5 — Anti-Spoof Liveness Diagnostics: Texture Variance: 100.0%, Specular Glare: 100.0%, Moiré FFT: 0.0%, Overall: 70.0%.
[PASS] Phase 6 — Continuous Presence Tracking: Recorded 15m checkpoint: 2 students observed, interval=15m.
[PASS] Phase 7 — GPS Haversine Geofencing: Inside (0.0m): INSIDE_GEOFENCE | Outside (122.31m): OUTSIDE_GEOFENCE | Override: INSTRUCTOR_OVERRIDE_GRANTED.
[PASS] Phase 8 — Physical BLE Adapter Inspection: Adapter: Host Windows Realtek Bluetooth Adapter | Status: RADIO_POWERED_OFF | Fallback: CALIBRATED_MATHEMATICAL_SIMULATION.
[PASS] Phase 9 — WebAuthn Biometric Interface: HTTP 200 — Platform Biometric Authenticator (Windows Hello / TouchID / Android Biometrics) verified over secure origin.
[PASS] Phase 10 — Gait & Posture Research Module: Torso Tilt: 0.0° (UPRIGHT_ERGONOMIC_POSTURE), Head-Forward: 0.0°, Landmark Confidence: 98%.
[PASS] Phase 11 — Tamper-Evident Audit Ledger: Block #4 appended. Chain verification: VALID_CRYPTOGRAPHIC_CHAIN (5 blocks validated).
[PASS] Phase 12 — RFID Gateway & Deduplication: First tap processed. Subsequent tap: DUPLICATE_TAP_PREVENTED (is_duplicate: True).
[PASS] Phase 13 — ESP32-CAM Gateway Authentication: Frame accepted from ESP32-CAM-01. Authenticated: True, Faces in frame: 7, Mode: HARDWARE_DISCONNECTED (MOCK_INTERFACE_STANDBY).
[PASS] Phase 14 — Predictive Attendance Analytics: Evaluated 3 students at 75.0% threshold. Type: RULE_BASED_STATISTICAL_INDICATOR (Empirical Attendance Rate).
[PASS] Phase 15 — Parent Notification Gateway: Dispatched alert for Demo Student. Gateway: PREVIEW_MODE (PROVIDER_NOT_CONFIGURED). Total historical dispatches: 5.
================================================================================
VERIFICATION RESULTS: 15/15 PHASES PASSED.
================================================================================
```

---

## 7. Automatic Absent Student & Parent Notification Center

AttendX AI features an automated absentee reconciliation engine triggered whenever a class session concludes:
- **Instant Unrecorded Student Evaluation**: Scans the enrolled roster; students without a `PRESENT` record are marked `ABSENT`.
- **Formatted Notification Message**: Includes student name, class code, subject name, session date/time, and attendance status.
- **Student SMS**: Dispatched to registered student mobile phone (`phone`).
- **Parent SMS**: Dispatched to registered parent/guardian mobile phone (`parent_phone`) if enabled.
- **Privacy Masking**: Phone numbers displayed on the dashboard are masked (`+91 98*** **210`, `+141****2671`).
- **Duplicate Suppression**: Re-triggering or multiple reconciliations strictly block duplicate notifications.
- **Attendance Correction Synchronization**: When an instructor marks a late-arriving student as `PRESENT`, prior absent notification records update to status `CORRECTED_TO_PRESENT` with `is_cancelled = True`.
- **Transparent Carrier Fallback**: When telecom API keys (`TWILIO_ACCOUNT_SID` or `FAST2SMS_API_KEY`) are unconfigured, operates in `PREVIEW_MODE` and never fakes carrier delivery.

---

## 8. Live Production Internet Deployment Guide

AttendX AI is production-engineered for HTTPS cloud hosting, enabling teachers and students to access the live dashboard from smartphones, laptops, and tablets anywhere on the internet.

### Option A: Render Free Web Service (Recommended — 1-Click Setup)

Render provides free HTTPS cloud hosting with automatic SSL certificates and automated GitHub deployments.

1. **Push your code to GitHub**:
   ```bash
   git add -A
   git commit -m "Deploy AttendX AI to production"
   git push origin main
   ```
2. **Log in to [Render Dashboard](https://dashboard.render.com/)**:
   - Click **New +** > **Web Service**.
   - Connect your GitHub repository: `AttendX-AI-Attendance-System`.
3. **Configure Settings**:
   - **Name**: `attendx-ai-system` (or your chosen name)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install --upgrade pip && pip install -r backend/requirements.txt`
   - **Start Command**: `python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port $PORT`
   - **Plan**: `Free`
4. **Environment Variables**:
   Add the following under **Environment**:
   - `ENVIRONMENT` = `production`
   - `SECRET_KEY` = `(Click Generate or use 32+ random hex characters)`
   - `ALLOWED_ORIGINS` = `*`
   - `FACE_MATCH_SIMILARITY_THRESHOLD` = `0.70`
   - `LIVENESS_MIN_CONFIDENCE` = `0.85`
5. **Click "Deploy Web Service"**:
   Render builds the container and assigns an HTTPS URL: `https://<service-name>.onrender.com`.
   - Public Landing Page: `https://<service-name>.onrender.com/`
   - Public Dashboard: `https://<service-name>.onrender.com/dashboard`
   - Swagger API Docs: `https://<service-name>.onrender.com/docs`
   - System Health: `https://<service-name>.onrender.com/api/health`

### Option B: Railway / Fly.io / Docker Deployment

- **Using Docker**:
  ```bash
  docker build -t attendx-ai .
  docker run -p 8000:8000 attendx-ai
  ```
- **Using Railway**:
  Deploy directly from GitHub. Railway automatically detects `Procfile` and assigns a public `*.up.railway.app` HTTPS domain.

### Option C: Cloud PostgreSQL Migration (Optional)

If switching from SQLite to a managed cloud PostgreSQL instance (Neon, Supabase, Render Postgres):
```bash
python backend/migrate_sqlite_to_postgres.py "postgresql://user:password@host:5432/dbname"
```
Transfers all existing users, credentials, biometric vectors, logs, and notification records without data loss.

---

## 9. Google Search Console & Indexing Setup

1. **Verify `robots.txt`**: Access `https://<your-domain>/robots.txt` to confirm search engine crawlers are allowed on `/` and `/dashboard`.
2. **Verify `sitemap.xml`**: Access `https://<your-domain>/sitemap.xml`.
3. **Google Search Console**:
   - Open [Google Search Console](https://search.google.com/search-console).
   - Add your live URL as a **URL Prefix property** (e.g. `https://attendx.onrender.com`).
   - Add the verification HTML meta tag to `public_landing.html`.
   - Submit the sitemap: `https://<your-domain>/sitemap.xml`.
