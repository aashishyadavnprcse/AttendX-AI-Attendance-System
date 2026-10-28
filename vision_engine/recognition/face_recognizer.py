"""
AttendX Vision Engine — Biometric Face Recognition Service
Extracts high-dimensional facial embedding vectors using InsightFace (ArcFace) or DeepFace,
and performs cosine similarity matching against the enrolled database.
"""

from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import cv2


class FaceRecognizer:
    """
    Manages face embedding extraction and vector matching against enrolled students.
    Supports InsightFace ArcFace models and DeepFace backends.
    """

    def __init__(
        self,
        similarity_threshold: float = 0.68,
        backend: str = "insightface",  # "insightface" | "deepface" | "fallback"
    ):
        self.similarity_threshold = similarity_threshold
        self.backend = backend
        self.enrolled_students: Dict[str, np.ndarray] = {}
        self.extractor = None

        self._initialize_backend()

    def _initialize_backend(self):
        """Initializes the preferred deep face recognition model."""
        if self.backend == "insightface":
            try:
                import insightface
                from insightface.app import FaceAnalysis

                print("[FaceRecognizer] Initializing InsightFace (buffalo_l)...")
                app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
                app.prepare(ctx_id=0, det_size=(640, 640))
                self.extractor = app
                print("[FaceRecognizer] InsightFace initialized successfully.")
                return
            except Exception as e:
                print(f"[FaceRecognizer] InsightFace unavailable ({e}), trying DeepFace...")
                self.backend = "deepface"

        if self.backend == "deepface":
            try:
                from deepface import DeepFace
                self.extractor = DeepFace
                print("[FaceRecognizer] DeepFace backend loaded.")
                return
            except Exception as e:
                print(f"[FaceRecognizer] DeepFace unavailable ({e}), falling back to lightweight embedder.")
                self.backend = "fallback"

    def enroll_student(self, student_id: str, embedding: List[float]):
        """Registers a student's enrolled embedding vector."""
        vec = np.array(embedding, dtype=np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        self.enrolled_students[student_id] = vec

    def extract_embedding(self, face_crop_bgr: np.ndarray) -> Optional[np.ndarray]:
        """
        Extracts 512-d normalized embedding vector from cropped face image.
        """
        if face_crop_bgr is None or face_crop_bgr.size == 0:
            return None

        # 1. InsightFace Pipeline
        if self.backend == "insightface" and self.extractor is not None:
            faces = self.extractor.get(face_crop_bgr)
            if faces and len(faces) > 0:
                emb = faces[0].embedding
                norm = np.linalg.norm(emb)
                return emb / norm if norm > 0 else emb

        # 2. DeepFace Pipeline
        if self.backend == "deepface" and self.extractor is not None:
            try:
                # Facenet512 or ArcFace
                reps = self.extractor.represent(
                    img_path=face_crop_bgr,
                    model_name="ArcFace",
                    enforce_detection=False,
                    align=True,
                )
                if reps and len(reps) > 0:
                    emb = np.array(reps[0]["embedding"], dtype=np.float32)
                    norm = np.linalg.norm(emb)
                    return emb / norm if norm > 0 else emb
            except Exception:
                pass

        # 3. Optimized Lightweight Feature Embedder (Fallback for instant offline dev/testing)
        resized = cv2.resize(face_crop_bgr, (112, 112))
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        # Compute gradient orientation histogram
        gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        mag, ang = cv2.cartToPolar(gx, gy, angleInDegrees=True)
        # Downsample into 128-dimensional spatial feature vector
        cells = cv2.resize(mag, (16, 8)).flatten()
        norm = np.linalg.norm(cells)
        return cells / norm if norm > 0 else cells

    def match_face(
        self, candidate_embedding: np.ndarray
    ) -> Tuple[Optional[str], float]:
        """
        Calculates cosine similarity against all enrolled vectors.
        Returns:
            (best_student_id, best_confidence) or (None, 0.0) if below threshold.
        """
        if candidate_embedding is None or len(self.enrolled_students) == 0:
            return None, 0.0

        best_student = None
        best_similarity = -1.0

        for student_id, enrolled_vec in self.enrolled_students.items():
            # Check dimensional compatibility
            if len(enrolled_vec) != len(candidate_embedding):
                continue

            similarity = float(np.dot(candidate_embedding, enrolled_vec))
            if similarity > best_similarity:
                best_similarity = similarity
                best_student = student_id

        # Clamp confidence score into [0.0, 1.0]
        confidence = float(max(0.0, min(1.0, best_similarity)))

        if confidence >= self.similarity_threshold:
            return best_student, round(confidence, 4)

        return None, round(confidence, 4)
