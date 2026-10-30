"""
AttendX AI — Real Computer Vision Biometric Face Engine
Integrates:
1. OpenCV YuNet (ONNX) — Real Deep Face Detection & 5 Facial Landmarks
2. OpenCV SFace (ONNX) — Real Deep Face Recognition (128-d Normalized Embeddings)
3. Texture & Reflection Analyzer — Real Heuristic Liveness Verification
"""

import base64
import os
import re
import sys
from typing import Dict, List, Optional, Tuple, Any
import cv2
import numpy as np

# Path to ONNX models
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

YUNET_PATH = os.path.join(BASE_DIR, "vision_engine", "models", "face_detection_yunet_2023mar.onnx")
SFACE_PATH = os.path.join(BASE_DIR, "vision_engine", "models", "face_recognition_sface_2021dec.onnx")

# Global model singletons
_detector = None
_recognizer = None
_texture_analyzer = None


def get_detector(score_threshold: float = 0.6):
    global _detector
    if _detector is None:
        if not os.path.exists(YUNET_PATH):
            raise FileNotFoundError(f"YuNet ONNX model not found at {YUNET_PATH}")
        _detector = cv2.FaceDetectorYN_create(
            YUNET_PATH,
            "",
            (320, 320),
            score_threshold=score_threshold,
            nms_threshold=0.3,
            top_k=50
        )
    return _detector


def get_recognizer():
    global _recognizer
    if _recognizer is None:
        if not os.path.exists(SFACE_PATH):
            raise FileNotFoundError(f"SFace ONNX model not found at {SFACE_PATH}")
        _recognizer = cv2.FaceRecognizerSF_create(SFACE_PATH, "")
    return _recognizer


def get_texture_analyzer():
    global _texture_analyzer
    if _texture_analyzer is None:
        from vision_engine.anti_spoof.texture_analyzer import TextureAndReflectionAnalyzer
        _texture_analyzer = TextureAndReflectionAnalyzer()
    return _texture_analyzer


def decode_image_base64(image_base64: str) -> np.ndarray:
    """Decodes standard base64 or Data URI string to BGR OpenCV image."""
    if not image_base64:
        raise ValueError("Empty image data provided.")

    if "," in image_base64:
        image_base64 = image_base64.split(",", 1)[1]

    image_base64 = re.sub(r"\s+", "", image_base64)
    img_bytes = base64.b64decode(image_base64)
    np_arr = np.frombuffer(img_bytes, dtype=np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if frame is None or frame.size == 0:
        raise ValueError("Could not decode valid image frame from base64 payload.")

    return frame


def detect_and_extract_faces(
    frame_bgr: np.ndarray,
    min_confidence: float = 0.6,
    check_liveness: bool = True
) -> List[Dict[str, Any]]:
    """
    Performs real deep face detection, landmark extraction, liveness evaluation,
    and 128-d deep facial embedding extraction for all human faces in frame.
    """
    h, w = frame_bgr.shape[:2]
    det = get_detector(score_threshold=min_confidence)
    rec = get_recognizer()
    analyzer = get_texture_analyzer()

    det.setInputSize((w, h))
    _, raw_faces = det.detect(frame_bgr)

    results = []
    if raw_faces is None or len(raw_faces) == 0:
        return results

    for idx, f in enumerate(raw_faces):
        # YuNet format: [x, y, w, h, x_re, y_re, x_le, y_le, x_nt, y_nt, x_rc, y_rc, x_lc, y_lc, score]
        box = [int(f[0]), int(f[1]), int(f[2]), int(f[3])]
        # Ensure bounding box is within frame boundaries
        box[0] = max(0, min(w - 1, box[0]))
        box[1] = max(0, min(h - 1, box[1]))
        box[2] = max(1, min(w - box[0], box[2]))
        box[3] = max(1, min(h - box[1], box[3]))

        landmarks = [float(coord) for coord in f[4:14]]
        det_score = float(f[14])

        # 1. Align face and extract 128-d SFace embedding
        aligned = rec.alignCrop(frame_bgr, f)
        raw_feat = rec.feature(aligned)
        norm = np.linalg.norm(raw_feat)
        norm_feat = (raw_feat / norm).flatten().tolist() if norm > 0 else raw_feat.flatten().tolist()

        # 2. Extract facial crop for anti-spoof analysis
        crop = frame_bgr[box[1]:box[1]+box[3], box[0]:box[0]+box[2]]
        liveness_data = {
            "is_genuine": True,
            "overall_liveness_score": 1.0,
            "reasons": [],
            "texture_score": 1.0,
            "reflection_score": 1.0,
            "moire_score": 1.0
        }
        if check_liveness and crop.size > 0:
            liveness_data = analyzer.evaluate(crop)

        results.append({
            "face_index": idx,
            "bounding_box": box,
            "landmarks": landmarks,
            "detection_score": round(det_score, 4),
            "embedding": norm_feat,
            "liveness": liveness_data
        })

    return results


def match_candidate_embedding(
    candidate_emb: List[float],
    enrolled_students: List[Dict[str, Any]],
    similarity_threshold: float = 0.50
) -> Tuple[Optional[Dict[str, Any]], float, str]:
    """
    Computes cosine similarity between candidate embedding and enrolled templates.
    Returns: (best_student_dict, best_confidence, decision_message)
    """
    if not candidate_emb or not enrolled_students:
        return None, 0.0, "No enrolled templates available for comparison."

    cand = np.array(candidate_emb, dtype=np.float32)
    norm_cand = np.linalg.norm(cand)
    if norm_cand > 0:
        cand = cand / norm_cand

    best_student = None
    best_sim = -1.0

    for s in enrolled_students:
        stored = s.get("embedding_vector")
        if not stored or len(stored) != len(candidate_emb):
            continue

        ref = np.array(stored, dtype=np.float32)
        norm_ref = np.linalg.norm(ref)
        if norm_ref > 0:
            ref = ref / norm_ref

        sim = float(np.dot(cand, ref))
        if sim > best_sim:
            best_sim = sim
            best_student = s

    confidence = round(float(max(0.0, min(1.0, best_sim))), 4)

    if best_student and confidence >= similarity_threshold:
        return (
            best_student,
            confidence,
            f"Verified identity match with {best_student.get('name')} ({confidence * 100:.1f}% confidence)."
        )

    return (
        None,
        confidence,
        f"Unknown individual. Top match confidence {confidence * 100:.1f}% is below threshold ({similarity_threshold * 100:.1f}%)."
    )


class MultiFaceTracker:
    """
    Maintains temporary face track IDs across consecutive video frames
    using 2D bounding box centroid Euclidean association.
    Enables CCTV stream tracking, trajectory stability, and duplicate rejection.
    """
    def __init__(self, max_distance: float = 90.0, max_disappeared: int = 15):
        self.next_track_id = 1
        self.tracks: Dict[int, Dict[str, Any]] = {}
        self.max_distance = max_distance
        self.max_disappeared = max_disappeared

    def update(self, detected_faces: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if len(detected_faces) == 0:
            for tid in list(self.tracks.keys()):
                self.tracks[tid]["disappeared"] += 1
                if self.tracks[tid]["disappeared"] > self.max_disappeared:
                    del self.tracks[tid]
            return []

        # Calculate centroids for input detections
        input_centroids = []
        for f in detected_faces:
            box = f["bounding_box"]
            cx = box[0] + (box[2] / 2.0)
            cy = box[1] + (box[3] / 2.0)
            input_centroids.append((cx, cy))

        if len(self.tracks) == 0:
            for idx, f in enumerate(detected_faces):
                tid = self.next_track_id
                self.next_track_id += 1
                self.tracks[tid] = {
                    "centroid": input_centroids[idx],
                    "disappeared": 0,
                    "seen_count": 1,
                    "last_box": f["bounding_box"]
                }
                f["track_id"] = tid
            return detected_faces

        # Associate existing tracks with closest detection
        track_ids = list(self.tracks.keys())
        track_centroids = [self.tracks[tid]["centroid"] for tid in track_ids]

        matched_tracks = set()
        matched_inputs = set()

        for in_idx, in_c in enumerate(input_centroids):
            best_dist = float("inf")
            best_tid = None
            for tr_idx, tid in enumerate(track_ids):
                if tid in matched_tracks:
                    continue
                tr_c = track_centroids[tr_idx]
                dist = np.sqrt((in_c[0] - tr_c[0]) ** 2 + (in_c[1] - tr_c[1]) ** 2)
                if dist < best_dist and dist <= self.max_distance:
                    best_dist = dist
                    best_tid = tid

            if best_tid is not None:
                matched_tracks.add(best_tid)
                matched_inputs.add(in_idx)
                self.tracks[best_tid]["centroid"] = in_c
                self.tracks[best_tid]["last_box"] = detected_faces[in_idx]["bounding_box"]
                self.tracks[best_tid]["disappeared"] = 0
                self.tracks[best_tid]["seen_count"] += 1
                detected_faces[in_idx]["track_id"] = best_tid
            else:
                new_tid = self.next_track_id
                self.next_track_id += 1
                self.tracks[new_tid] = {
                    "centroid": in_c,
                    "disappeared": 0,
                    "seen_count": 1,
                    "last_box": detected_faces[in_idx]["bounding_box"]
                }
                detected_faces[in_idx]["track_id"] = new_tid

        for tid in list(self.tracks.keys()):
            if tid not in matched_tracks and tid in self.tracks:
                self.tracks[tid]["disappeared"] += 1
                if self.tracks[tid]["disappeared"] > self.max_disappeared:
                    del self.tracks[tid]

        return detected_faces


_multi_face_tracker = MultiFaceTracker()


def get_multi_face_tracker():
    global _multi_face_tracker
    return _multi_face_tracker

