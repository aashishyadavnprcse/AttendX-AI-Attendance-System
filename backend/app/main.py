from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.session import engine, Base, SessionLocal
from app.models.user import User, UserRole
from app.models.session import ClassSession
from app.models.attendance import AttendanceLog, AttendanceStatus
from app.core.security import get_password_hash
from app.routers import auth, session, attendance, analytics


def seed_initial_demo_data():
    """
    Seeds demo administrator, teacher, students with biometric templates,
    and an active class session for instant plug-and-play testing.
    """
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            print("[AttendX Backend] Seeding initial test users and biometric signatures...")
            # Demo 128-dimensional synthetic embedding templates
            sarah_embedding = [0.05 * (i % 7) for i in range(128)]
            alex_embedding = [0.03 * (i % 5) for i in range(128)]

            # 1. Admin
            admin = User(
                name="System Administrator",
                email="admin@attendx.ai",
                hashed_password=get_password_hash("Admin@123"),
                role=UserRole.ADMIN,
                avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150"
            )
            # 2. Teacher
            teacher = User(
                name="Dr. Elena Rostova",
                email="teacher@attendx.ai",
                hashed_password=get_password_hash("Teacher@123"),
                role=UserRole.TEACHER,
                avatar_url="https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150"
            )
            # 3. Students
            student1 = User(
                name="Sarah Chen",
                email="sarah.chen@student.attendx.ai",
                hashed_password=get_password_hash("Student@123"),
                role=UserRole.STUDENT,
                roll_number="CS-2026-001",
                embedding_vector=sarah_embedding,
                avatar_url="https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150",
                parent_name="Wei Chen",
                parent_phone="+14155552671"
            )
            student2 = User(
                name="Alex Mercer",
                email="alex.mercer@student.attendx.ai",
                hashed_password=get_password_hash("Student@123"),
                role=UserRole.STUDENT,
                roll_number="CS-2026-002",
                embedding_vector=alex_embedding,
                avatar_url="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150",
                parent_name="Robert Mercer",
                parent_phone="+14155558923"
            )

            db.add_all([admin, teacher, student1, student2])
            db.commit()

            # Seed Active Class Session with 20m Geofence Perimeter
            demo_session = ClassSession(
                teacher_id=teacher.id,
                subject_name="Neural Networks & Computer Vision",
                classroom_latitude=37.7749,
                classroom_longitude=-122.4194,
                geofence_radius_meters=20.0,
                require_geofence=True,
                is_active=True
            )
            db.add(demo_session)
            db.commit()

            # Seed Attendance Log for Sarah Chen
            demo_log = AttendanceLog(
                student_id=student1.id,
                session_id=demo_session.id,
                status=AttendanceStatus.PRESENT,
                confidence_score=0.985,
                verification_method="FACE_BIOMETRIC_LIVENESS",
                gps_latitude=37.7749,
                gps_longitude=-122.4194,
                liveness_score=0.992
            )
            db.add(demo_log)
            db.commit()
            print("[AttendX Backend] Database seeded successfully.")
    except Exception as e:
        print(f"[AttendX Backend] Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB Schema tables
    Base.metadata.create_all(bind=engine)
    # Seed initial test data
    seed_initial_demo_data()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Ultra-modern AI Smart Attendance, Anti-Spoof Biometric Verification & Analytics Backend.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Middleware for modern frontend frameworks (Vite, Next.js, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(session.router, prefix=settings.API_V1_STR)
app.include_router(attendance.router, prefix=settings.API_V1_STR)
app.include_router(analytics.router, prefix=settings.API_V1_STR)


@app.get("/api/health", tags=["System"])
def health_check():
    return {
        "status": "online",
        "service": "AttendX Core API",
        "version": "1.0.0",
        "biometrics_engine": "Active",
        "anti_spoofing": "Active",
    }
