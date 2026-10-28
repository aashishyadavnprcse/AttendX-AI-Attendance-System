"""
AttendX Vision Engine — Core Biometric Service
Integrates MediaPipe FaceMesh, 3D Liveness Detection (EAR & Screen Replay Analysis),
and Deep Facial Embedding Vector Matching.
"""

from datetime import datetime, timezone
import json
import time
from typing import Dict, Any, Optional, Tuple, List
import cv2
import numpy as np

try:
    import mediapipe as mp
except ImportError:
    mp = None

from vision_engine.anti_spoof.ear_detector import BlinkLivenessDetector
from vision_engine.anti_spoof.texture_analyzer import TextureAndReflectionAnalyzer
from vision_engine.recognition.face_recognizer import FaceRecognizer


class AttendXVisionService:
    """
    Real-time Computer Vision Service delivering end-to-end biometric verification,
    3D anti-spoofing (EAR blinking + screen reflection analysis), and JSON telemetry.
    """

    def __init__(
        self,
        similarity_threshold: float = 0.68,
        ear_threshold: float = 0.21,
        require_blink: bool = False,
    ):
        """
        :param similarity_threshold: Minimum cosine similarity to authenticate a student.
        :param ear_threshold: Eye aspect ratio threshold for eyelid closure.
        :param require_blink: If True, student must register at least one real blink during session.
        """
        self.require_blink = require_blink

        # Subsystems
        self.blink_detector = BlinkLivenessDetector(ear_threshold=ear_threshold)
        self.texture_analyzer = TextureAndReflectionAnalyzer()
        self.recognizer = FaceRecognizer(similarity_threshold=similarity_threshold)

        # MediaPipe Face Mesh Setup
        self.mp_face_mesh = None
        self.face_mesh = None
        if mp is not None:
            self.mp_face_mesh = mp.solutions.face_mesh
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.6,
                min_tracking_confidence=0.6,
            )
        else:
            print("[AttendXVisionService] Warning: mediapipe not found. Run pip install mediapipe.")

    def enroll_student(self, student_id: str, embedding: List[float]):
        """Enrolls a student facial embedding vector into local vector registry."""
        self.recognizer.enroll_student(student_id, embedding)

    @staticmethod
    def _get_bounding_box(landmarks, frame_shape: Tuple[int, int]) -> Tuple[int, int, int, int]:
        """Calculates bounding box [x1, y1, x2, y2] from MediaPipe landmarks."""
        h, w = frame_shape
        x_coords = [int(pt.x * w) for pt in landmarks]
        y_coords = [int(pt.y * h) for pt in landmarks]

        # Add 12% padding for full facial structure
        pad_x = int((max(x_coords) - min(x_coords)) * 0.12)
        pad_y = int((max(y_coords) - min(y_coords)) * 0.15)

        x1 = max(0, min(x_coords) - pad_x)
        y1 = max(0, min(y_coords) - pad_y)
        x2 = min(w, max(x_coords) + pad_x)
        y2 = min(h, max(y_coords) + pad_y)
        return x1, y1, x2, y2

    def process_frame(self, frame_bgr: np.ndarray) -> Dict[str, Any]:
        """
        Executes real-time frame inspection:
        1. MediaPipe 468/478 3D landmark extraction
        2. Eye Aspect Ratio (EAR) blink verification
        3. Texture, Reflection & Moiré screen replay attack analysis
        4. Facial embedding extraction & database vector matching
        5. Formatted JSON payload return
        """
        start_time = time.perf_counter()
        now_iso = datetime.now(timezone.utc).isoformat()

        if frame_bgr is None or frame_bgr.size == 0:
            return {
                "status": "UNKNOWN",
                "student_id": None,
                "confidence_score": 0.0,
                "message": "Empty or corrupted frame.",
                "timestamp": now_iso,
            }

        h, w, _ = frame_bgr.shape
        rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        # 1. Landmark & Face Detection
        results = None
        if self.face_mesh is not None:
            results = self.face_mesh.process(rgb_frame)

        if not results or not results.multi_face_landmarks:
            latency = (time.perf_counter() - start_time) * 1000.0
            return {
                "status": "UNKNOWN",
                "student_id": None,
                "confidence_score": 0.0,
                "message": "No human face detected in frame.",
                "latency_ms": round(latency, 2),
                "timestamp": now_iso,
            }

        landmarks = results.multi_face_landmarks[0].landmark
        landmarks_3d = [np.array([lm.x, lm.y, lm.z]) for lm in landmarks]

        # 2. Eye Aspect Ratio (EAR) & Blink Check
        blink_occurred, avg_ear, left_ear, right_ear = self.blink_detector.process_frame(landmarks_3d)

        # 3. Crop Face for Texture & Replay Analysis
        x1, y1, x2, y2 = self._get_bounding_box(landmarks, (h, w))
        face_crop = frame_bgr[y1:y2, x1:x2]

        texture_metrics = self.texture_analyzer.evaluate(face_crop)

        # 4. Synthesize Liveness Decision
        is_spoof = False
        spoof_reasons = list(texture_metrics.get("reasons", []))

        # Check screen replay / printed photo flags
        if not texture_metrics["is_genuine"]:
            is_spoof = True

        # Check blink requirement if enforced
        if self.require_blink and self.blink_detector.total_blinks_detected == 0:
            is_spoof = True
            spoof_reasons.append("Pending active human eye blink challenge.")

        liveness_data = {
            "passed": not is_spoof,
            "blink_detected": self.blink_detector.total_blinks_detected > 0 or blink_occurred,
            "blink_count": self.blink_detector.total_blinks_detected,
            "ear_avg": round(avg_ear, 4),
            "ear_left": round(left_ear, 4),
            "ear_right": round(right_ear, 4),
            "texture_score": texture_metrics["texture_score"],
            "reflection_score": texture_metrics["reflection_score"],
            "moire_score": texture_metrics["moire_score"],
            "overall_liveness_score": texture_metrics["overall_liveness_score"],
            "reasons": spoof_reasons,
        }

        # If spoof detected, immediately reject and return SPOOF_DETECTED
        if is_spoof:
            latency = (time.perf_counter() - start_time) * 1000.0
            return {
                "status": "SPOOF_DETECTED",
                "student_id": None,
                "confidence_score": texture_metrics["overall_liveness_score"],
                "liveness": liveness_data,
                "bbox": [x1, y1, x2, y2],
                "latency_ms": round(latency, 2),
                "timestamp": now_iso,
            }

        # 5. Extract Embedding & Match Against Database
        candidate_emb = self.recognizer.extract_embedding(face_crop)
        matched_id, confidence = self.recognizer.match_face(candidate_emb)

        status_result = "SUCCESS" if (matched_id is not None) else "UNKNOWN"

        latency = (time.perf_counter() - start_time) * 1000.0
        return {
            "status": status_result,
            "student_id": matched_id,
            "confidence_score": confidence,
            "liveness": liveness_data,
            "bbox": [x1, y1, x2, y2],
            "latency_ms": round(latency, 2),
            "timestamp": now_iso,
        }

    def process_and_json(self, frame_bgr: np.ndarray) -> str:
        """Helper returning raw formatted JSON string."""
        data = self.process_frame(frame_bgr)
        return json.dumps(data, indent=2)
