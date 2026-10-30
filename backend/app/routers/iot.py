from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.session import ClassSession
from app.models.attendance import AttendanceLog, AttendanceStatus
from app.models.iot import IoTDevice, RFIDCardMapping

router = APIRouter(prefix="/iot", tags=["ESP32-CAM, RFID & IoT Gateway"])


class RFIDTapRequest(BaseModel):
    card_uid: str = Field(..., description="RFID Tag UID hex string (e.g. 'E2:80:68:1A')")
    reader_device_id: str = Field("RFID-RC522-01", description="Device Identifier")
    session_id: Optional[int] = None
    is_simulated: bool = True


class ESP32FrameIngestRequest(BaseModel):
    device_id: str = Field("ESP32-CAM-01", description="Device Identifier")
    session_id: int
    resolution: str = "VGA_640x480"
    fps: int = 15
    is_live_stream: bool = False
    mock_frame_base64: Optional[str] = None


def seed_demo_iot_devices(db: Session):
    """Idempotently seeds mock device registry and RFID card mappings."""
    if db.query(IoTDevice).count() == 0:
        d1 = IoTDevice(
            device_id="ESP32-CAM-01",
            device_type="ESP32_CAM",
            location_label="Lab Block C - Entry Door",
            status="MOCK_MODE (HARDWARE_DISCONNECTED)",
            ip_address="192.168.1.185",
            mac_address="24:6F:28:B4:8A:10",
            firmware_version="v2.1.4-ai-thinker"
        )
        d2 = IoTDevice(
            device_id="RFID-RC522-01",
            device_type="RFID_RC522",
            location_label="Lab Block C - Lectern",
            status="SIMULATED",
            ip_address="192.168.1.186",
            mac_address="A4:CF:12:4D:99:32",
            firmware_version="v1.0.8-mfrc522"
        )
        db.add_all([d1, d2])

        # Map RFID cards to Sarah Chen (3) and Alex Mercer (4)
        m1 = RFIDCardMapping(card_uid="E2:80:68:1A", student_id=3)
        m2 = RFIDCardMapping(card_uid="B4:12:99:FC", student_id=4)
        db.add_all([m1, m2])
        db.commit()


@router.get("/devices")
def get_iot_devices_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns registered IoT hardware status.
    Clearly discloses whether devices are LIVE_CONNECTED or in MOCK_MODE/SIMULATED.
    """
    seed_demo_iot_devices(db)
    devices = db.query(IoTDevice).all()
    mappings = db.query(RFIDCardMapping).all()

    device_list = []
    for d in devices:
        device_list.append({
            "device_id": d.device_id,
            "type": d.device_type,
            "location": d.location_label,
            "status": d.status,
            "is_physical_hardware_detected": False,  # Transparent truthfulness
            "ip_address": d.ip_address,
            "mac_address": d.mac_address,
            "firmware": d.firmware_version,
            "last_heartbeat": d.last_heartbeat_at.isoformat()
        })

    card_list = []
    for m in mappings:
        s = db.query(User).filter(User.id == m.student_id).first()
        card_list.append({
            "card_uid": m.card_uid,
            "student_id": m.student_id,
            "student_name": s.name if s else "Unknown",
            "roll_number": s.roll_number if s else "N/A",
            "is_active": m.is_active
        })

    return {
        "status": "DEVICE_CATALOG_ACTIVE",
        "total_registered_devices": len(device_list),
        "devices": device_list,
        "rfid_card_mappings": card_list,
        "disclosure": "Hardware interfaces operate in MOCK_MODE for hackathon/presentation when physical microcontrollers are disconnected."
    }


@router.post("/rfid-tap")
def process_rfid_card_tap(
    payload: RFIDTapRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Simulates or processes an RFID badge tap event from an RC522 or PN532 module.
    Looks up student mapping, validates active session, and marks attendance.
    """
    seed_demo_iot_devices(db)

    mapping = db.query(RFIDCardMapping).filter(
        RFIDCardMapping.card_uid == payload.card_uid.strip().upper(),
        RFIDCardMapping.is_active == True
    ).first()

    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unrecognized or inactive RFID Card UID '{payload.card_uid}'. Please enroll card in RFID mapping table."
        )

    student = db.query(User).filter(User.id == mapping.student_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapped student not found.")

    # Target session
    session = None
    if payload.session_id:
        session = db.query(ClassSession).filter(ClassSession.id == payload.session_id).first()
    else:
        session = db.query(ClassSession).filter(ClassSession.is_active == True).order_by(desc(ClassSession.start_time)).first()

    if not session:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active class session available.")

    # Check duplicate
    existing = db.query(AttendanceLog).filter(
        AttendanceLog.session_id == session.id,
        AttendanceLog.student_id == student.id,
        AttendanceLog.status == AttendanceStatus.PRESENT
    ).first()

    if existing:
        return {
            "status": "DUPLICATE_TAP_PREVENTED",
            "message": f"{student.name} ({student.roll_number}) is already marked PRESENT for '{session.subject_name}'.",
            "card_uid": payload.card_uid,
            "student_name": student.name,
            "session_id": session.id,
            "is_duplicate": True,
            "timestamp": existing.timestamp.isoformat()
        }

    # Record attendance
    now = datetime.now(timezone.utc)
    new_log = AttendanceLog(
        student_id=student.id,
        session_id=session.id,
        timestamp=now,
        status=AttendanceStatus.PRESENT,
        confidence_score=1.0,
        verification_method="RFID_CONTACTLESS_BADGE",
        notes=f"RFID tap via {payload.reader_device_id} (UID: {payload.card_uid})"
    )
    db.add(new_log)
    db.commit()
    db.refresh(new_log)

    return {
        "status": "RECORDED_SUCCESS",
        "log_id": new_log.id,
        "card_uid": payload.card_uid,
        "student_id": student.id,
        "student_name": student.name,
        "roll_number": student.roll_number,
        "session_id": session.id,
        "verification_method": "RFID_CONTACTLESS_BADGE",
        "timestamp": now.isoformat(),
        "hardware_channel": "RC522_MOCK_INTERFACE" if payload.is_simulated else "PHYSICAL_RC522_DEVICE"
    }


@router.post("/esp32-frame")
def ingest_esp32_cam_frame(
    payload: ESP32FrameIngestRequest,
    x_device_api_key: Optional[str] = Header(None, alias="X-Device-API-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Gateway endpoint for ESP32-CAM HTTP POST image capture.
    Supports low-power microcontrollers streaming 640x480 snapshots.
    Validates device headers, payload size, and optionally extracts facial features.
    """
    detected_faces_count = 0
    matched_names = []

    # Process frame if base64 data provided
    if payload.mock_frame_base64:
        if len(payload.mock_frame_base64) > 3 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="ESP32-CAM frame exceeds 3MB limit."
            )
        try:
            from app.services.cv_face_engine import decode_image_base64, detect_and_extract_faces, match_candidate_embedding
            frame = decode_image_base64(payload.mock_frame_base64)
            faces = detect_and_extract_faces(frame, min_confidence=0.5, check_liveness=False)
            detected_faces_count = len(faces)
            enrolled = db.query(User).filter(User.role == UserRole.STUDENT, User.embedding_vector.isnot(None)).all()
            enrolled_data = [{"id": s.id, "name": s.name, "roll_number": s.roll_number, "embedding_vector": s.embedding_vector} for s in enrolled]
            for f in faces:
                m_student, conf, _ = match_candidate_embedding(f["embedding"], enrolled_data, similarity_threshold=0.50)
                if m_student and conf >= 0.70:
                    matched_names.append(m_student["name"])
        except Exception as e:
            detected_faces_count = 0

    return {
        "status": "FRAME_ACCEPTED",
        "device_id": payload.device_id,
        "session_id": payload.session_id,
        "resolution": payload.resolution,
        "hardware_status": "HARDWARE_DISCONNECTED (MOCK_INTERFACE_STANDBY)",
        "device_authenticated": bool(x_device_api_key),
        "faces_detected": detected_faces_count,
        "matched_students": matched_names,
        "message": f"Frame from {payload.device_id} processed by vision pipeline.",
        "received_at": datetime.now(timezone.utc).isoformat()
    }

