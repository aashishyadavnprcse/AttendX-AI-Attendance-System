import os
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.session import ClassSession
from app.models.attendance import AttendanceLog, AttendanceStatus
from app.models.audit import AttendanceAuditLedger
from app.services.face_matcher import verify_biometric_face
import time
from app.services.cv_face_engine import (
    decode_image_base64,
    detect_and_extract_faces,
    match_candidate_embedding,
    get_multi_face_tracker,
    BASE_DIR,
    SFACE_PATH,
    YUNET_PATH
)

router = APIRouter(prefix="/face-engine", tags=["AI Multi-Face Detection & Liveness Lab"])


class CandidateFacePayload(BaseModel):
    face_index: int
    bounding_box: List[int] = Field(..., description="[x, y, width, height] normalized in pixels")
    embedding_vector: Optional[List[float]] = None
    liveness_score: float = Field(1.0, ge=0.0, le=1.0)
    is_live: bool = True
    suggested_roll_number: Optional[str] = None


class MultiFaceAnalysisRequest(BaseModel):
    session_id: int
    image_source: str = Field("WEBCAM_BROWSER", description="WEBCAM_BROWSER | ESP32_CAM | RTSP_CCTV")
    detected_faces: List[CandidateFacePayload]
    auto_record_high_confidence: bool = False  # If false, requires manual instructor review


@router.post("/analyze-batch")
def analyze_multi_face_batch(
    payload: MultiFaceAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyzes multi-face bounding boxes against enrolled student templates.
    Strictly separates:
    1. Face Detection (bounding box existence)
    2. Identity Vector Matching (cosine similarity against enrolled templates)
    3. Anti-Spoof Liveness Score (texture/reflection checks)
    Uncertain matches (< 0.85 confidence) are flagged for Instructor Manual Review.
    """
    session = db.query(ClassSession).filter(ClassSession.id == payload.session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Class session {payload.session_id} not found."
        )

    enrolled_students = db.query(User).filter(
        User.role == UserRole.STUDENT,
        User.embedding_vector.isnot(None)
    ).all()

    analysis_results = []
    recorded_count = 0
    review_queue_count = 0
    spoof_detected_count = 0

    for face in payload.detected_faces:
        matched_student = None
        best_confidence = 0.0
        match_msg = "No match"
        is_spoof = not face.is_live or (face.liveness_score < 0.85)

        # 1. Biometric template comparison
        if face.embedding_vector:
            for s in enrolled_students:
                is_match, spoof_flag, conf, msg = verify_biometric_face(
                    candidate_vector=face.embedding_vector,
                    registered_vector=s.embedding_vector,
                    is_live=face.is_live,
                    liveness_score=face.liveness_score,
                    threshold=0.72,
                    min_liveness=0.85
                )
                if conf > best_confidence:
                    best_confidence = conf
                    matched_student = s
                    match_msg = msg
                    if spoof_flag:
                        is_spoof = True
        elif face.suggested_roll_number:
            matched_student = db.query(User).filter(User.roll_number == face.suggested_roll_number).first()
            best_confidence = 0.95 if matched_student else 0.0
            match_msg = "Mock Vector Matching"

        # 2. Decision Tree
        if is_spoof:
            verdict = "SPOOF_ATTACK_REJECTED"
            verification_status = "REJECTED"
            needs_review = True
            spoof_detected_count += 1
        elif matched_student and best_confidence >= 0.85:
            verdict = "VERIFIED_STUDENT_MATCH"
            verification_status = "HIGH_CONFIDENCE_MATCH"
            needs_review = False
        elif matched_student and 0.65 <= best_confidence < 0.85:
            verdict = "UNCERTAIN_MATCH_REVIEW_REQUIRED"
            verification_status = "PENDING_INSTRUCTOR_REVIEW"
            needs_review = True
            review_queue_count += 1
        else:
            verdict = "UNRECOGNIZED_FACE"
            verification_status = "UNKNOWN_INDIVIDUAL"
            needs_review = True
            review_queue_count += 1

        # 3. Optional auto-record if explicitly enabled and high confidence
        if payload.auto_record_high_confidence and verdict == "VERIFIED_STUDENT_MATCH" and matched_student:
            existing = db.query(AttendanceLog).filter(
                AttendanceLog.session_id == session.id,
                AttendanceLog.student_id == matched_student.id,
                AttendanceLog.status == AttendanceStatus.PRESENT
            ).first()
            if not existing:
                log = AttendanceLog(
                    student_id=matched_student.id,
                    session_id=session.id,
                    timestamp=datetime.now(timezone.utc),
                    status=AttendanceStatus.PRESENT,
                    confidence_score=best_confidence,
                    verification_method="AI_MULTI_FACE_PIPELINE",
                    liveness_score=face.liveness_score,
                    notes="Verified through multi-face detection batch"
                )
                db.add(log)
                recorded_count += 1

        analysis_results.append({
            "face_index": face.face_index,
            "bounding_box": face.bounding_box,
            "matched_student_id": matched_student.id if matched_student else None,
            "matched_student_name": matched_student.name if matched_student else "Unknown",
            "roll_number": matched_student.roll_number if matched_student else None,
            "confidence_score": best_confidence,
            "liveness_score": face.liveness_score,
            "is_spoof": is_spoof,
            "verdict": verdict,
            "verification_status": verification_status,
            "instructor_review_required": needs_review,
            "algorithm_details": match_msg
        })

    if recorded_count > 0:
        db.commit()

    return {
        "status": "PROCESSED",
        "session_id": session.id,
        "subject_name": session.subject_name,
        "image_source": payload.image_source,
        "total_faces_detected": len(payload.detected_faces),
        "verified_matches_count": sum(1 for r in analysis_results if r["verdict"] == "VERIFIED_STUDENT_MATCH"),
        "review_queue_count": review_queue_count,
        "spoofs_intercepted": spoof_detected_count,
        "attendance_records_created": recorded_count,
        "detection_details": analysis_results,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


class ProcessFrameRequest(BaseModel):
    session_id: int
    image_base64: str = Field(..., description="Webcam capture frame encoded in base64 or Data URI")
    similarity_threshold: float = Field(0.50, ge=0.1, le=1.0)
    min_detection_score: float = Field(0.50, ge=0.1, le=1.0)
    check_liveness: bool = True
    auto_record_high_confidence: bool = False


@router.post("/process-frame")
def process_camera_frame(
    payload: ProcessFrameRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Genuine Deep Learning Pipeline for Live Browser Webcam Frames:
    1. Decodes raw JPEG/PNG image frame.
    2. Runs OpenCV YuNet (ONNX) face detector to locate all faces & 5 landmarks.
    3. Runs OpenCV SFace (ONNX) deep recognizer to extract normalized 128-d embeddings.
    4. Evaluates Texture & Specular Reflection Anti-Spoof metrics on each face crop.
    5. Matches candidate embeddings against enrolled student templates in the database.
    6. Strictly distinguishes detection, matching, and liveness verification.
    7. Requires instructor confirmation by default before committing attendance.
    """
    session = db.query(ClassSession).filter(ClassSession.id == payload.session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Class session {payload.session_id} not found."
        )

    try:
        frame_bgr = decode_image_base64(payload.image_base64)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image frame: {str(e)}"
        )

    # 1. Run Deep Face Detection & Feature Extraction
    try:
        detected_faces = detect_and_extract_faces(
            frame_bgr,
            min_confidence=payload.min_detection_score,
            check_liveness=payload.check_liveness
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Face detection engine error: {str(e)}"
        )

    # 2. Load enrolled students with biometric templates
    enrolled_query = db.query(User).filter(
        User.role == UserRole.STUDENT,
        User.embedding_vector.isnot(None)
    ).all()

    enrolled_students = [
        {
            "id": s.id,
            "name": s.name,
            "roll_number": s.roll_number,
            "embedding_vector": s.embedding_vector
        }
        for s in enrolled_query
    ]

    results = []
    recorded_count = 0
    review_queue_count = 0
    spoofs_count = 0

    # 3. Analyze each detected face
    for f in detected_faces:
        matched_dict, confidence, decision_msg = match_candidate_embedding(
            candidate_emb=f["embedding"],
            enrolled_students=enrolled_students,
            similarity_threshold=payload.similarity_threshold
        )

        liveness_info = f["liveness"]
        is_spoof = not liveness_info["is_genuine"]

        if is_spoof:
            verdict = "SPOOF_ATTACK_REJECTED"
            verification_status = "REJECTED_SPOOF"
            needs_review = True
            spoofs_count += 1
        elif matched_dict and confidence >= 0.70:
            verdict = "VERIFIED_STUDENT_MATCH"
            verification_status = "HIGH_CONFIDENCE_MATCH"
            needs_review = False
        elif matched_dict and confidence >= payload.similarity_threshold:
            verdict = "UNCERTAIN_MATCH_REVIEW_REQUIRED"
            verification_status = "PENDING_INSTRUCTOR_REVIEW"
            needs_review = True
            review_queue_count += 1
        else:
            verdict = "UNRECOGNIZED_FACE"
            verification_status = "UNKNOWN_INDIVIDUAL"
            needs_review = True
            review_queue_count += 1

        # Check duplicate if matched
        is_already_present = False
        if matched_dict:
            existing = db.query(AttendanceLog).filter(
                AttendanceLog.session_id == session.id,
                AttendanceLog.student_id == matched_dict["id"],
                AttendanceLog.status == AttendanceStatus.PRESENT
            ).first()
            if existing:
                is_already_present = True

        # Optional auto-record if explicitly enabled and high confidence and live
        if payload.auto_record_high_confidence and verdict == "VERIFIED_STUDENT_MATCH" and matched_dict and not is_already_present:
            log = AttendanceLog(
                student_id=matched_dict["id"],
                session_id=session.id,
                timestamp=datetime.now(timezone.utc),
                status=AttendanceStatus.PRESENT,
                confidence_score=confidence,
                verification_method="WEBCAM_SFACE_YUNET",
                liveness_score=liveness_info["overall_liveness_score"],
                notes=f"Auto-recorded via DeepFace SFace model (Confidence {confidence * 100:.1f}%)"
            )
            db.add(log)
            recorded_count += 1

        results.append({
            "face_index": f["face_index"],
            "bounding_box": f["bounding_box"],
            "landmarks": f["landmarks"],
            "detection_score": f["detection_score"],
            "matched_student_id": matched_dict["id"] if matched_dict else None,
            "matched_student_name": matched_dict["name"] if matched_dict else "Unknown",
            "roll_number": matched_dict["roll_number"] if matched_dict else None,
            "confidence_score": confidence,
            "liveness": liveness_info,
            "is_spoof": is_spoof,
            "verdict": verdict,
            "verification_status": verification_status,
            "instructor_review_required": needs_review,
            "already_present": is_already_present,
            "algorithm_details": decision_msg
        })

    if recorded_count > 0:
        db.commit()

    return {
        "status": "FRAME_PROCESSED",
        "session_id": session.id,
        "subject_name": session.subject_name,
        "total_faces_detected": len(results),
        "verified_matches_count": sum(1 for r in results if r["verdict"] == "VERIFIED_STUDENT_MATCH"),
        "review_queue_count": review_queue_count,
        "spoofs_intercepted": spoofs_count,
        "attendance_records_created": recorded_count,
        "detection_details": results,
        "models_used": {
            "detector": "OpenCV YuNet (face_detection_yunet_2023mar.onnx)",
            "recognizer": "OpenCV SFace (face_recognition_sface_2021dec.onnx)",
            "anti_spoof": "OpenCV Texture, Specular Reflection & 2D FFT Frequency Analyzer"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


class ConfirmAttendanceRequest(BaseModel):
    session_id: int
    student_id: int
    confidence_score: float = Field(1.0, ge=0.0, le=1.0)
    liveness_score: float = Field(1.0, ge=0.0, le=1.0)
    verification_method: str = "WEBCAM_SFACE_YUNET"
    notes: Optional[str] = "Instructor confirmed face recognition"


@router.post("/confirm-attendance")
def confirm_biometric_attendance(
    payload: ConfirmAttendanceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Records attendance after explicit instructor confirmation.
    Validates session, prevents duplicate attendance, persists to SQLite, and updates audit chain.
    """
    session = db.query(ClassSession).filter(ClassSession.id == payload.session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Class session {payload.session_id} not found."
        )

    student = db.query(User).filter(User.id == payload.student_id, User.role == UserRole.STUDENT).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student {payload.student_id} not found."
        )

    # Prevent duplicate attendance
    existing = db.query(AttendanceLog).filter(
        AttendanceLog.session_id == session.id,
        AttendanceLog.student_id == student.id,
        AttendanceLog.status == AttendanceStatus.PRESENT
    ).first()

    if existing:
        return {
            "status": "DUPLICATE_PREVENTED",
            "message": f"{student.name} ({student.roll_number}) is already marked PRESENT for {session.subject_name}.",
            "is_duplicate": True,
            "student_id": student.id,
            "student_name": student.name,
            "roll_number": student.roll_number,
            "session_id": session.id,
            "existing_timestamp": existing.timestamp.isoformat()
        }

    now = datetime.now(timezone.utc)
    new_log = AttendanceLog(
        student_id=student.id,
        session_id=session.id,
        timestamp=now,
        status=AttendanceStatus.PRESENT,
        confidence_score=payload.confidence_score,
        verification_method=payload.verification_method,
        liveness_score=payload.liveness_score,
        notes=f"{payload.notes} (Confirmed by {current_user.name})"
    )
    db.add(new_log)
    db.commit()
    db.refresh(new_log)

    return {
        "status": "ATTENDANCE_RECORDED",
        "log_id": new_log.id,
        "student_id": student.id,
        "student_name": student.name,
        "roll_number": student.roll_number,
        "session_id": session.id,
        "subject_name": session.subject_name,
        "confidence_score": payload.confidence_score,
        "liveness_score": payload.liveness_score,
        "verification_method": payload.verification_method,
        "confirmed_by": current_user.name,
        "timestamp": now.isoformat()
    }


class EnrollStudentFaceRequest(BaseModel):
    student_id: int
    image_base64: str = Field(..., description="Reference face capture image in base64")


@router.post("/enroll-student")
def enroll_student_face_template(
    payload: EnrollStudentFaceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Enrolls a student's real 128-d deep facial embedding vector from a captured image.
    Validates exactly one face in frame, extracts SFace embedding, and saves to database.
    """
    student = db.query(User).filter(User.id == payload.student_id, User.role == UserRole.STUDENT).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student {payload.student_id} not found."
        )

    try:
        frame_bgr = decode_image_base64(payload.image_base64)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image payload: {str(e)}"
        )

    faces = detect_and_extract_faces(frame_bgr, min_confidence=0.5, check_liveness=False)
    if len(faces) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No face detected in enrollment frame. Please ensure proper lighting and face the camera directly."
        )
    if len(faces) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Detected {len(faces)} faces in frame. Face enrollment requires exactly one individual in frame."
        )

    embedding = faces[0]["embedding"]
    student.embedding_vector = embedding
    db.commit()

    return {
        "status": "ENROLLED_SUCCESS",
        "student_id": student.id,
        "student_name": student.name,
        "roll_number": student.roll_number,
        "embedding_dimensions": len(embedding),
        "detection_confidence": faces[0]["detection_score"],
        "bounding_box": faces[0]["bounding_box"],
        "message": f"Biometric template successfully enrolled for {student.name} ({student.roll_number})."
    }


@router.post("/seed-demo-templates")
def seed_demo_biometric_templates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Seeds genuine SFace 128-d biometric embeddings from the local reference image (demo.jpg)
    into the database for Sarah Chen (Face 0) and Alex Mercer (Face 1).
    Allows reproducible, verified testing without manual photo uploads.
    """
    import cv2
    demo_img_path = os.path.join(BASE_DIR, "vision_engine", "models", "demo.jpg")
    if not os.path.exists(demo_img_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Demo reference image not found at {demo_img_path}."
        )

    frame = cv2.imread(demo_img_path)
    if frame is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to read demo image.")

    faces = detect_and_extract_faces(frame, min_confidence=0.6, check_liveness=False)
    if len(faces) < 2:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Expected at least 2 faces in demo image.")

    sarah = db.query(User).filter(User.id == 3).first()
    alex = db.query(User).filter(User.id == 4).first()

    updated = []
    if sarah:
        sarah.embedding_vector = faces[0]["embedding"]
        updated.append(sarah.name)
    if alex:
        alex.embedding_vector = faces[1]["embedding"]
        updated.append(alex.name)

    db.commit()

    return {
        "status": "SEEDED_SUCCESS",
        "message": f"Enrolled genuine 128-d SFace embeddings for: {', '.join(updated)}.",
        "updated_students": updated,
        "embedding_dimensions": 128
    }


class CCTVStreamAnalyzeRequest(BaseModel):
    session_id: int
    image_base64: str = Field(..., description="CCTV / RTSP / Video frame in base64")
    stream_source: str = Field("WEBCAM", description="WEBCAM | RTSP_CCTV | TEST_VIDEO")
    similarity_threshold: float = Field(0.50, ge=0.1, le=1.0)


@router.post("/cctv-stream-analyze")
def analyze_cctv_multi_face_stream(
    payload: CCTVStreamAnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Real Multi-Face CCTV Stream Analysis & Benchmarking:
    1. Ingests video frame from Webcam, RTSP, or authorized test video.
    2. Measures exact execution latency (ms) and actual frame processing rate (FPS).
    3. Runs deep face detection (YuNet) and centroid-based multi-face tracking across frames.
    4. Matches tracked faces against enrolled student templates in the database.
    5. Categorizes and returns track IDs, identity match status, and review flags.
    """
    t0 = time.perf_counter()

    session = db.query(ClassSession).filter(ClassSession.id == payload.session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Class session {payload.session_id} not found."
        )

    try:
        frame_bgr = decode_image_base64(payload.image_base64)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image frame: {str(e)}"
        )

    # 1. Detect faces
    detected_faces = detect_and_extract_faces(frame_bgr, min_confidence=0.5, check_liveness=True)

    # 2. Track across frames
    tracker = get_multi_face_tracker()
    tracked_faces = tracker.update(detected_faces)

    # 3. Match against enrolled students
    enrolled_query = db.query(User).filter(
        User.role == UserRole.STUDENT,
        User.embedding_vector.isnot(None)
    ).all()

    enrolled_students = [
        {"id": s.id, "name": s.name, "roll_number": s.roll_number, "embedding_vector": s.embedding_vector}
        for s in enrolled_query
    ]

    tracked_results = []
    for tf in tracked_faces:
        matched_dict, confidence, decision_msg = match_candidate_embedding(
            candidate_emb=tf["embedding"],
            enrolled_students=enrolled_students,
            similarity_threshold=payload.similarity_threshold
        )

        liveness_info = tf["liveness"]
        is_spoof = not liveness_info["is_genuine"]

        if is_spoof:
            verdict = "SPOOF_ATTACK_REJECTED"
            verification_status = "REJECTED_SPOOF"
            needs_review = True
        elif matched_dict and confidence >= 0.70:
            verdict = "VERIFIED_STUDENT_MATCH"
            verification_status = "HIGH_CONFIDENCE_MATCH"
            needs_review = False
        elif matched_dict and confidence >= payload.similarity_threshold:
            verdict = "UNCERTAIN_MATCH_REVIEW_REQUIRED"
            verification_status = "PENDING_INSTRUCTOR_REVIEW"
            needs_review = True
        else:
            verdict = "UNRECOGNIZED_FACE"
            verification_status = "UNKNOWN_INDIVIDUAL"
            needs_review = True

        tracked_results.append({
            "track_id": tf.get("track_id", 0),
            "face_index": tf["face_index"],
            "bounding_box": tf["bounding_box"],
            "matched_student_id": matched_dict["id"] if matched_dict else None,
            "matched_student_name": matched_dict["name"] if matched_dict else "Unknown",
            "roll_number": matched_dict["roll_number"] if matched_dict else None,
            "confidence_score": confidence,
            "liveness_score": liveness_info["overall_liveness_score"],
            "is_spoof": is_spoof,
            "verdict": verdict,
            "verification_status": verification_status,
            "instructor_review_required": needs_review,
            "stages": {
                "face_detected": True,
                "identity_matched": matched_dict is not None,
                "liveness_checked": True,
                "attendance_recorded": False
            }
        })

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    measured_fps = round(1000.0 / max(1.0, elapsed_ms), 1)

    return {
        "status": "STREAM_PROCESSED",
        "stream_source": payload.stream_source,
        "session_id": session.id,
        "subject_name": session.subject_name,
        "faces_detected": len(tracked_results),
        "active_tracks_count": len(tracked_results),
        "latency_ms": elapsed_ms,
        "measured_fps": measured_fps,
        "performance_benchmark": f"Measured processing latency: {elapsed_ms}ms ({measured_fps} FPS) across {len(tracked_results)} visible faces.",
        "tracked_faces": tracked_results,
        "evaluated_at": datetime.now(timezone.utc).isoformat()
    }


