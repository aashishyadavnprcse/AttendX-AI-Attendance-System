"""
AttendX Vision Engine — Eye Aspect Ratio (EAR) & Blink Liveness Module
Extracts 3D facial landmarks using MediaPipe Face Mesh to detect genuine human eye blinks.
"""

from typing import Tuple, List, Optional
import numpy as np


class BlinkLivenessDetector:
    """
    Computes Eye Aspect Ratio (EAR) based on MediaPipe 468/478 Face Mesh topology.
    Implements a temporal hysteresis state machine to accurately register physiological blinks.
    """

    # Canonical MediaPipe FaceMesh eye indices:
    # Left eye: [outer, inner, top1, bottom1, top2, bottom2]
    LEFT_EYE_LANDMARKS = {
        'corner_outer': 33,
        'corner_inner': 133,
        'top_1': 160,
        'bottom_1': 144,
        'top_2': 158,
        'bottom_2': 153,
    }

    # Right eye:
    RIGHT_EYE_LANDMARKS = {
        'corner_outer': 362,
        'corner_inner': 263,
        'top_1': 385,
        'bottom_1': 380,
        'top_2': 387,
        'bottom_2': 373,
    }

    def __init__(
        self,
        ear_threshold: float = 0.21,
        consec_closed_frames: int = 2,
        consec_open_frames: int = 2,
    ):
        """
        :param ear_threshold: EAR value below which the eye is classified as CLOSED.
        :param consec_closed_frames: Consecutive frames eyes must remain closed to avoid noise.
        :param consec_open_frames: Consecutive frames eyes must re-open to confirm blink completion.
        """
        self.ear_threshold = ear_threshold
        self.consec_closed_frames = consec_closed_frames
        self.consec_open_frames = consec_open_frames

        # State machine tracking
        self.closed_frame_counter = 0
        self.open_frame_counter = 0
        self.in_blink_phase = False
        self.total_blinks_detected = 0

    @staticmethod
    def _euclidean_distance(pt1: np.ndarray, pt2: np.ndarray) -> float:
        """Calculates 3D Euclidean distance between two landmarks."""
        return float(np.linalg.norm(pt1 - pt2))

    def calculate_ear(self, landmarks_3d: List[np.ndarray], eye_indices: dict) -> float:
        """
        Calculates Eye Aspect Ratio (EAR):
        EAR = (||p2 - p6|| + ||p3 - p5||) / (2 * ||p1 - p4||)
        """
        p1 = landmarks_3d[eye_indices['corner_outer']]
        p4 = landmarks_3d[eye_indices['corner_inner']]
        p2 = landmarks_3d[eye_indices['top_1']]
        p6 = landmarks_3d[eye_indices['bottom_1']]
        p3 = landmarks_3d[eye_indices['top_2']]
        p5 = landmarks_3d[eye_indices['bottom_2']]

        # Vertical distances
        vertical_dist_1 = self._euclidean_distance(p2, p6)
        vertical_dist_2 = self._euclidean_distance(p3, p5)

        # Horizontal distance
        horizontal_dist = self._euclidean_distance(p1, p4)

        if horizontal_dist < 1e-6:
            return 0.0

        ear = (vertical_dist_1 + vertical_dist_2) / (2.0 * horizontal_dist)
        return float(ear)

    def process_frame(
        self, landmarks_3d: List[np.ndarray]
    ) -> Tuple[bool, float, float, float]:
        """
        Processes current landmark frame.
        Returns:
            (blink_just_completed, avg_ear, left_ear, right_ear)
        """
        left_ear = self.calculate_ear(landmarks_3d, self.LEFT_EYE_LANDMARKS)
        right_ear = self.calculate_ear(landmarks_3d, self.RIGHT_EYE_LANDMARKS)
        avg_ear = (left_ear + right_ear) / 2.0

        blink_completed = False

        if avg_ear < self.ear_threshold:
            self.closed_frame_counter += 1
            self.open_frame_counter = 0
            if self.closed_frame_counter >= self.consec_closed_frames:
                self.in_blink_phase = True
        else:
            if self.in_blink_phase:
                self.open_frame_counter += 1
                if self.open_frame_counter >= self.consec_open_frames:
                    self.total_blinks_detected += 1
                    self.in_blink_phase = False
                    self.closed_frame_counter = 0
                    self.open_frame_counter = 0
                    blink_completed = True
            else:
                self.closed_frame_counter = 0
                self.open_frame_counter = 0

        return blink_completed, avg_ear, left_ear, right_ear

    def reset(self):
        """Resets the blink detector state."""
        self.closed_frame_counter = 0
        self.open_frame_counter = 0
        self.in_blink_phase = False
        self.total_blinks_detected = 0
