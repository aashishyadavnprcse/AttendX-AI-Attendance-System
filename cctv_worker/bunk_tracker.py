"""
AttendX AI Research — Continuous Presence & Bunk Tracker
Tracks student desk presence across sequential 15-minute lecture intervals.
Detects when a student checks in at the start of class but vacates their seat midway.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


class BunkTracker:
    """
    Maintains temporal presence states for all registered seats/students in a session.
    Flags students who leave the lecture hall without authorized departure.
    """

    def __init__(self, max_allowed_missing_intervals: int = 1):
        """
        :param max_allowed_missing_intervals: Number of intervals a student can be absent
               (e.g., bathroom break = 1 interval) before being officially flagged for bunking.
        """
        self.max_allowed_missing_intervals = max_allowed_missing_intervals

        # State storage: student_id -> state dict
        self.student_states: Dict[int, Dict[str, Any]] = {}

    def register_enrolled_students(self, seat_registry: Dict[str, Dict[str, Any]]):
        """
        Initializes student tracking states from the classroom seat registry.
        """
        for seat_id, data in seat_registry.items():
            sid = data["student_id"]
            self.student_states[sid] = {
                "student_id": sid,
                "roll_number": data.get("roll_number"),
                "seat_id": seat_id,
                "initially_present": False,
                "currently_present": False,
                "consecutive_missing": 0,
                "total_intervals_observed": 0,
                "total_intervals_present": 0,
                "bunk_detected": False,
                "bunk_flagged_interval": None,
                "attention_history": [],
            }

    def update_interval(
        self,
        interval_index: int,
        seat_observations: Dict[str, Dict[str, Any]],
        attention_map: Dict[str, Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Processes an observation interval (e.g. Every 15 minutes).
        Returns a list of student status updates ready for backend batch transmission.
        """
        updates = []

        for seat_id, obs in seat_observations.items():
            sid = obs.get("student_id")
            if not sid or sid not in self.student_states:
                continue

            state = self.student_states[sid]
            state["total_intervals_observed"] += 1
            is_occupied = obs.get("occupied", False)
            state["currently_present"] = is_occupied

            # Record initial presence at class start (interval 0)
            if interval_index == 0 and is_occupied:
                state["initially_present"] = True

            # Attention score from pose estimator
            att_data = attention_map.get(seat_id, {})
            current_att_score = att_data.get("attention_score", 0.0) if is_occupied else 0.0
            head_pose_status = att_data.get("status", "SEAT_VACANT") if is_occupied else "SEAT_VACANT"

            if is_occupied:
                state["total_intervals_present"] += 1
                state["consecutive_missing"] = 0
                state["attention_history"].append(current_att_score)

                # If student returned after missing, clear immediate bunk flag if permitted
                flag_reason = None
            else:
                state["consecutive_missing"] += 1
                state["attention_history"].append(0.0)

                # Check if this qualifies as a Bunk:
                # Student was present earlier in session, but vacated their seat midway
                if (state["initially_present"] or state["total_intervals_present"] > 0) and (
                    state["consecutive_missing"] > self.max_allowed_missing_intervals
                ):
                    state["bunk_detected"] = True
                    if state["bunk_flagged_interval"] is None:
                        state["bunk_flagged_interval"] = interval_index

                    flag_reason = (
                        f"BUNK_DETECTED: Vacated seat {seat_id} midway during lecture. "
                        f"Missing for {state['consecutive_missing']} consecutive intervals."
                    )
                else:
                    flag_reason = "Temporarily absent / vacated seat."

            update_payload = {
                "student_id": sid,
                "roll_number": state.get("roll_number"),
                "seat_id": seat_id,
                "is_present": is_occupied,
                "bunk_detected": state["bunk_detected"],
                "attention_score": round(current_att_score, 4),
                "head_pose_status": head_pose_status,
                "flag_reason": flag_reason,
            }
            updates.append(update_payload)

        return updates

    def get_classroom_summary(self) -> Dict[str, Any]:
        """Calculates global presence and attention statistics."""
        total = len(self.student_states)
        occupied = sum(1 for s in self.student_states.values() if s["currently_present"])
        bunked = sum(1 for s in self.student_states.values() if s["bunk_detected"])

        all_scores = [
            s["attention_history"][-1]
            for s in self.student_states.values()
            if s["attention_history"] and s["currently_present"]
        ]
        avg_att = round(sum(all_scores) / len(all_scores), 4) if all_scores else 0.0

        return {
            "total_registered_seats": total,
            "currently_occupied_seats": occupied,
            "bunks_flagged": bunked,
            "average_attention_score": avg_att,
        }
