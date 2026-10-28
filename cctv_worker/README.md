# AttendX AI Research — Classroom CCTV Background Worker

Autonomous AI worker service using **YOLOv8** (Person Detection & Spatial Seat Mapping) and **MediaPipe Pose** (Head Pitch & Yaw Attention Estimation) to monitor student presence and continuous engagement.

---

## ⚡ Core Architecture

```
cctv_worker/
├── yolo_detector.py      # YOLOv8 Person detector & centroid-to-desk Euclidean matching
├── pose_estimator.py     # MediaPipe Pose 33 3D skeletal landmarks & Head Pose Attention model
├── bunk_tracker.py       # Multi-interval presence & seat abandonment state machine
├── worker.py             # Scheduled 15-minute background worker & FastAPI batch dispatcher
├── test_worker.py        # Multi-interval classroom simulation test suite
├── requirements.txt      # Worker dependencies
└── README.md             # Documentation & mathematical derivations
```

---

## 📐 Scientific Formulation

### 1. Head Pitch (Looking Down at Smartphone / Sleeping)
Let $E_y = \frac{y_{\text{left\_ear}} + y_{\text{right\_ear}}}{2}$ and $S_y = \frac{y_{\text{left\_shoulder}} + y_{\text{right\_shoulder}}}{2}$.  
We compute the downward nose displacement ratio relative to the anatomical head-neck span:
$$\Delta_{\text{pitch}} = \frac{y_{\text{nose}} - E_y}{S_y - E_y}$$
- **Facing Whiteboard**: $\Delta_{\text{pitch}} \in [0.15, 0.35]$ (nose sits high, level with ears)
- **Looking Down at Smartphone**: $\Delta_{\text{pitch}} > 0.48$ (head pitches forward, nose drops towards shoulders)

$$\text{Penalty}_{\text{pitch}} = \text{clamp}\left(\frac{\Delta_{\text{pitch}} - 0.35}{0.30}, 0.0, 1.0\right)$$

### 2. Head Yaw (Facing Board vs. Looking Sideways)
We evaluate bilateral facial symmetry between the nose and outer ear anchors:
$$A_{\text{yaw}} = \frac{|d_{\text{left}} - d_{\text{right}}|}{d_{\text{left}} + d_{\text{right}}}$$
where $d_{\text{left}} = |x_{\text{nose}} - x_{\text{left\_ear}}|$ and $d_{\text{right}} = |x_{\text{nose}} - x_{\text{right\_ear}}|$.
- **Facing Whiteboard**: $A_{\text{yaw}} < 0.20$
- **Turned Sideways**: $A_{\text{yaw}} > 0.45$

$$\text{Penalty}_{\text{yaw}} = \text{clamp}\left(\frac{A_{\text{yaw}} - 0.22}{0.40}, 0.0, 1.0\right)$$

### 3. Aggregate Attention Score
$$S_{\text{att}} = \text{clamp}\left(1.0 - (0.60 \cdot \text{Penalty}_{\text{pitch}} + 0.40 \cdot \text{Penalty}_{\text{yaw}}), 0.0, 1.0\right)$$

---

## 🚨 Bunk Tracker State Machine

Students who check in during the initial attendance scan (Interval 0) are continuously monitored across subsequent 15-minute intervals:

```
[Interval 0: Present at Desk] 
         ↓
[Interval 1: Vacated Desk] ──→ Grace Period (Bathroom / Water break)
         ↓
[Interval 2: Desk Still Vacant] ──→ ⚠️ BUNK DETECTED!
         ↓
Dispatches batch update to FastAPI (/api/analytics/continuous-monitoring)
Updates student session record from PRESENT to ABSENT (BUNKED MIDWAY)
```

---

## 🚀 Execution & Usage

### 1. Install Dependencies
```bash
cd cctv_worker
pip install -r requirements.txt
```

### 2. Run the Worker
```bash
# Monitor CCTV webcam feed at standard 15-minute intervals
python worker.py --backend-url http://127.0.0.1:8000/api --session-id 1 --interval 15.0

# Fast testing mode (e.g. 10-second intervals):
python worker.py --interval 0.166
```

### 3. Run Offline Simulation Test Suite
```bash
python test_worker.py
```
