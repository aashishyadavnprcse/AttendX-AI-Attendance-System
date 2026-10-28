"""
AttendX AI Research — YOLOv8 Classroom Person & Spatial Seat Detector
Detects student bodies in CCTV / wide-angle classroom camera feeds and
maps spatial centroids to registered classroom desk coordinates.
"""

from typing import List, Dict, Tuple, Any, Optional
import math
import numpy as np

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None


class YOLOPersonDetector:
    """
    YOLOv8-based person detector optimized for wide-angle classroom CCTV cameras.
    """

    def __init__(
        self,
        model_name: str = "yolov8n.pt",
        confidence_threshold: float = 0.45,
    ):
        self.confidence_threshold = confidence_threshold
        self.model = None

        if YOLO is not None:
            try:
                print(f"[YOLOPersonDetector] Loading {model_name}...")
                self.model = YOLO(model_name)
                print("[YOLOPersonDetector] YOLOv8 model loaded successfully.")
            except Exception as e:
                print(f"[YOLOPersonDetector] Warning: Could not initialize YOLOv8 ({e}). Using heuristic mode.")
        else:
            print("[YOLOPersonDetector] Ultralytics not installed. Operating in fallback mode.")

    def detect_persons(self, frame_bgr: np.ndarray) -> List[Dict[str, Any]]:
        """
        Runs person detection on frame.
        Returns:
            List of detected persons: [{'bbox': [x1, y1, x2, y2], 'centroid': (cx, cy), 'confidence': float}]
        """
        if frame_bgr is None or frame_bgr.size == 0:
            return []

        h, w, _ = frame_bgr.shape
        detections = []

        if self.model is not None:
            # Run inference filtering for class 0 (person)
            results = self.model(frame_bgr, classes=[0], conf=self.confidence_threshold, verbose=False)
            for r in results:
                for box in r.boxes:
                    coords = box.xyxy[0].cpu().numpy()
                    x1, y1, x2, y2 = [int(v) for v in coords]
                    conf = float(box.conf[0].cpu().numpy())
                    cx = (x1 + x2) // 2
                    cy = (y1 + y2) // 2

                    detections.append({
                        "bbox": [x1, y1, x2, y2],
                        "centroid": (cx, cy),
                        "confidence": round(conf, 4),
                    })
        else:
            # Synthetic / Heuristic fallback for offline execution
            # Divides frame into 3 sample person bounding boxes for testing
            for i in range(3):
                x1 = int(w * (0.2 + i * 0.25))
                y1 = int(h * 0.3)
                x2 = x1 + int(w * 0.15)
                y2 = y1 + int(h * 0.45)
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2
                detections.append({
                    "bbox": [x1, y1, x2, y2],
                    "centroid": (cx, cy),
                    "confidence": 0.88,
                })

        return detections

    @staticmethod
    def map_persons_to_seats(
        detections: List[Dict[str, Any]],
        seat_registry: Dict[str, Dict[str, Any]],
        max_distance_px: float = 120.0,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Associates detected persons with pre-registered classroom desk seats
        using Euclidean distance minimization between centroid and seat anchor.
        
        :param seat_registry: Dict mapping seat_id -> {'student_id': int, 'roll_number': str, 'anchor_xy': (x, y)}
        :returns: Dict mapping seat_id -> {'occupied': bool, 'person_bbox': list, 'distance': float}
        """
        seat_status = {}

        # Initialize all seats as vacant
        for seat_id, seat_data in seat_registry.items():
            seat_status[seat_id] = {
                "occupied": False,
                "student_id": seat_data.get("student_id"),
                "roll_number": seat_data.get("roll_number"),
                "person_bbox": None,
                "distance": 9999.0,
                "confidence": 0.0,
            }

        unassigned_detections = list(detections)

        for seat_id, seat_data in seat_registry.items():
            sx, sy = seat_data["anchor_xy"]
            best_det_idx = None
            min_dist = max_distance_px

            for idx, det in enumerate(unassigned_detections):
                cx, cy = det["centroid"]
                dist = math.hypot(cx - sx, cy - sy)
                if dist < min_dist:
                    min_dist = dist
                    best_det_idx = idx

            if best_det_idx is not None:
                matched_det = unassigned_detections.pop(best_det_idx)
                seat_status[seat_id]["occupied"] = True
                seat_status[seat_id]["person_bbox"] = matched_det["bbox"]
                seat_status[seat_id]["distance"] = round(min_dist, 2)
                seat_status[seat_id]["confidence"] = matched_det["confidence"]

        return seat_status
