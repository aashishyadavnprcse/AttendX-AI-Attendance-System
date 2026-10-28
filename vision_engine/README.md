# AttendX AI Vision Engine

Real-Time 3D Biometric Liveness Anti-Spoofing and Facial Recognition Service built with **OpenCV**, **MediaPipe**, **InsightFace**, and **DeepFace**.

---

## ⚡ Core Architecture

```
vision_engine/
├── anti_spoof/
│   ├── ear_detector.py        # MediaPipe 468 3D Face Mesh Eye Aspect Ratio (EAR) & Blink state machine
│   └── texture_analyzer.py    # Moiré pattern FFT, specular screen reflection & Laplacian texture analyzer
├── recognition/
│   └── face_recognizer.py     # ArcFace / InsightFace / DeepFace feature extractor & Cosine Similarity vector matcher
├── service.py                 # Core AttendXVisionService orchestrating detection, liveness & verification
├── stream_processor.py        # High-performance video stream HUD overlay (#06B6D4 Cyan, #10B981 Emerald, #F43F5E Rose)
├── test_pipeline.py           # Offline synthetic test verification suite
└── requirements.txt           # Dependencies
```

---

## 🛡️ Anti-Spoofing 3D Liveness Safeguards

### 1. Eye Aspect Ratio (EAR) Blink Detection
Calculates 3D Euclidean distances between the eyelid landmarks on MediaPipe's Face Mesh:
$$\text{EAR} = \frac{\|p_2 - p_6\| + \|p_3 - p_5\|}{2 \cdot \|p_1 - p_4\|}$$
- Eye closed: $\text{EAR} < 0.21$
- State machine tracks hysteresis over consecutive frames to confirm authentic human physiological blinking and eliminate printed 2D photograph attacks.

### 2. Screen & Photo Replay Attack Analysis
1. **Specular Reflection Glare**: Detects harsh screen backlight reflection clusters in HSV/RGB space that do not naturally occur on human skin tissue.
2. **2D FFT Moiré Patterns**: Detects periodic subpixel matrix frequency harmonics produced when digital screens are recorded through camera lenses.
3. **Laplacian Skin Micro-Texture Variance**: Measures high-frequency gradient variance to distinguish genuine skin micro-pores and wrinkles from flat paper prints and out-of-focus digital screens.

---

## 🚀 Setup & Execution

### 1. Install Dependencies
```bash
cd vision_engine
pip install -r requirements.txt
```

### 2. Run Real-Time Camera Stream with AttendX HUD
```bash
# Starts live camera feed (default device 0)
python stream_processor.py

# Or specify a custom RTSP stream or video file:
python stream_processor.py rtsp://admin:pass@192.168.1.50:554/stream1
```

### 3. Run Offline Test Suite
```bash
python test_pipeline.py
```

---

## 📋 JSON Telemetry Specification

The service outputs standardized JSON responses ready for integration into the AttendX FastAPI backend (`/api/attendance/verify`):

```json
{
  "status": "SUCCESS",
  "student_id": "CS-2026-001 (Sarah Chen)",
  "confidence_score": 0.9842,
  "liveness": {
    "passed": true,
    "blink_detected": true,
    "blink_count": 2,
    "ear_avg": 0.2854,
    "ear_left": 0.2881,
    "ear_right": 0.2827,
    "texture_score": 0.9412,
    "reflection_score": 0.9654,
    "moire_score": 0.9231,
    "overall_liveness_score": 0.9432,
    "reasons": []
  },
  "bbox": [280, 140, 710, 580],
  "latency_ms": 24.8,
  "timestamp": "2026-10-28T16:15:20.123456Z"
}
```

If a mobile screen replay or photo attack is intercepted:
```json
{
  "status": "SPOOF_DETECTED",
  "student_id": null,
  "confidence_score": 0.3821,
  "liveness": {
    "passed": false,
    "reasons": [
      "Specular glass reflection detected (possible mobile screen replay).",
      "High-frequency periodic grid detected (Moiré pattern screen attack)."
    ]
  },
  "latency_ms": 21.2
}
```
