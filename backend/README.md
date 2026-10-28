# AttendX - AI Smart Attendance & Analytics Platform (Backend)

High-performance, modular FastAPI backend engineered for real-time facial recognition attendance, anti-spoof liveness detection, session orchestration, and live dashboard analytics.

---

## 🏗 Modular Architecture Overview

```
backend/
├── app/
│   ├── core/
│   │   ├── config.py           # Pydantic v2 application settings & environment tokens
│   │   ├── security.py         # Bcrypt password hashing & JWT encoding/decoding
│   │   └── dependencies.py     # OAuth2 / Bearer JWT validation & RBAC (Role-Based Access Control)
│   ├── db/
│   │   └── session.py          # SQLAlchemy Engine, SessionLocal, Base, get_db dependency
│   ├── models/
│   │   ├── user.py             # User (id, name, email, role, roll_number, embedding_vector, avatar_url)
│   │   ├── session.py          # ClassSession (id, teacher_id, subject_name, start_time, end_time, is_active)
│   │   └── attendance.py       # AttendanceLog (student_id, session_id, status: PRESENT/ABSENT/SPOOF_DETECTED, confidence)
│   ├── schemas/
│   │   ├── user.py             # User schemas for creation, login, and response
│   │   ├── token.py            # JWT token response & payload claims
│   │   ├── session.py          # ClassSession start/stop request & response
│   │   ├── attendance.py       # Biometric verification request with GPS & liveness payload
│   │   └── analytics.py        # Real-time analytics & telemetry response models
│   ├── services/
│   │   └── face_matcher.py     # Cosine similarity vector matching & anti-spoof liveness engine
│   ├── routers/
│   │   ├── auth.py             # POST /api/auth/register, /login, GET /me
│   │   ├── session.py          # POST /api/session/start, /stop, GET /active
│   │   ├── attendance.py       # POST /api/attendance/verify
│   │   └── analytics.py        # GET /api/analytics/realtime
│   └── main.py                 # FastAPI application factory, CORS, DB migration & demo seeding
├── requirements.txt            # Python dependencies
└── .env.example                # Sample environment variables
```

---

## 🚀 Quickstart & Setup

### 1. Create Virtual Environment & Install Dependencies
```bash
cd backend
python -m venv venv

# Windows
.\venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```env
PROJECT_NAME="AttendX AI Smart Attendance"
SECRET_KEY="attendx_super_secret_jwt_key_replace_in_production"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=480

# For PostgreSQL in production:
# DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/attendx"

# For instant zero-config testing:
DATABASE_URL="sqlite:///./attendx.db"

FACE_MATCH_SIMILARITY_THRESHOLD=0.75
LIVENESS_MIN_CONFIDENCE=0.85
```

### 3. Launch Development Server
```bash
uvicorn app.main:app --reload --port 8000
```
- **Interactive Swagger API Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check**: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

---

## 🔑 Pre-Seeded Demo Accounts

Upon initial launch, the database is auto-seeded with test profiles and an active session:

| Role | Email | Password | Details |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@attendx.ai` | `Admin@123` | Full system control |
| **Teacher** | `teacher@attendx.ai` | `Teacher@123` | Has active session: *Neural Networks & Computer Vision* |
| **Student** | `sarah.chen@student.attendx.ai` | `Student@123` | Roll No: `CS-2026-001`, 128-d face embedding enrolled |
| **Student** | `alex.mercer@student.attendx.ai` | `Student@123` | Roll No: `CS-2026-002`, 128-d face embedding enrolled |

---

## 📡 API Endpoint Reference

### 1. Authentication (`/api/auth`)
- **`POST /api/auth/register`**: Register new student, teacher, or admin.
- **`POST /api/auth/login`**: Authenticate using email and password to receive JWT Bearer token.
- **`GET /api/auth/me`**: Current user profile with biometric enrollment status.

### 2. Session Management (`/api/session`)
- **`POST /api/session/start`**: (Teacher / Admin) Starts a new live session for a subject.
- **`POST /api/session/stop`**: (Teacher / Admin) Terminates an ongoing session.
- **`GET /api/session/active`**: Returns all ongoing class sessions.

### 3. Biometric Attendance Verification (`/api/attendance`)
- **`POST /api/attendance/verify`**:
  ```json
  {
    "session_id": 1,
    "student_id": 3,
    "embedding_vector": [0.0, 0.05, 0.10, ...],
    "latitude": 37.7749,
    "longitude": -122.4194,
    "is_live": true,
    "liveness_score": 0.985
  }
  ```
  - Computes cosine similarity between live face vector and enrolled profile.
  - Verifies anti-spoof liveness criteria.
  - Returns `PRESENT` or `SPOOF_DETECTED` with confidence metrics.

### 4. Live Analytics Telemetry (`/api/analytics`)
- **`GET /api/analytics/realtime`**:
  Returns real-time dashboard telemetry:
  - `total_students`
  - `present_count`
  - `absent_count`
  - `spoof_count`
  - `attendance_rate` (%)
  - `spoof_rejection_rate` (%)
  - `recent_logs` (last 10 events with student avatars, confidence, and timestamps)
