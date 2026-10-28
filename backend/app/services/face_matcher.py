import math
from typing import List, Tuple


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """
    Computes cosine similarity between two embedding vectors.
    Returns float in range [-1.0, 1.0].
    """
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0

    try:
        import numpy as np
        a = np.array(v1, dtype=np.float32)
        b = np.array(v2, dtype=np.float32)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
    except ImportError:
        # Pure Python fallback
        dot = sum(x * y for x, y in zip(v1, v2))
        norm_a = math.sqrt(sum(x * x for x in v1))
        norm_b = math.sqrt(sum(y * y for y in v2))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


def verify_biometric_face(
    candidate_vector: List[float],
    registered_vector: List[float],
    is_live: bool,
    liveness_score: float,
    threshold: float = 0.75,
    min_liveness: float = 0.85
) -> Tuple[bool, bool, float, str]:
    """
    Verifies biometric candidate against enrolled face vector and anti-spoof telemetry.
    Returns: (is_match, is_spoof, confidence_score, status_message)
    """
    # 1. Anti-Spoof Liveness verification
    if not is_live or (liveness_score is not None and liveness_score < min_liveness):
        return False, True, round(liveness_score or 0.0, 4), "Anti-spoofing alert: Non-live face or presentation attack detected."

    # 2. Check enrolled profile
    if not registered_vector:
        return False, False, 0.0, "Student has no registered biometric facial template on file."

    # 3. Vector Cosine Similarity
    similarity = cosine_similarity(candidate_vector, registered_vector)
    confidence = round(max(0.0, min(1.0, similarity)), 4)

    if similarity >= threshold:
        return True, False, confidence, f"Biometric verification successful. Match confidence: {confidence * 100:.2f}%"
    else:
        return False, True, confidence, f"Biometric mismatch: Identity confidence below threshold ({confidence * 100:.2f}% < {threshold * 100:.2f}%)."
