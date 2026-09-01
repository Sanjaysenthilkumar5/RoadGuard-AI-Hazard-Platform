# 🛡️ RoadGuard AI — Intelligent Road Hazard Detection, Mapping & Risk Intelligence Platform

> **AI-Powered Municipal Pavement Monitoring, Severity Scoring, Geospatial Hotspot Clustering & Field Maintenance Platform**

---

## 📌 1. Executive Overview

**RoadGuard AI** is an enterprise-grade smart-city road monitoring and risk intelligence system. It transforms standard monocular RGB imagery, video footage, and dashcam camera streams into actionable civil infrastructure intelligence.

Rather than a simple bounding-box demo, RoadGuard AI implements a multi-tier pipeline:
`DETECT → UNDERSTAND → LOCATE → PRIORITIZE → ACT → VERIFY`

```
              DASHCAM / SMARTPHONE / CCTV FEED
                            │
                            ▼
              COMPUTER VISION SERVICE (YOLO)
              ┌─────────────────────────────┐
              │ • 15 Defect Classifiers     │
              │ • Monocular Depth Estimation│
              │ • Perspective Sizing (cm)   │
              └──────────────┬──────────────┘
                             │
                             ▼
              MULTI-FRAME TEMPORAL TRACKER
              ┌─────────────────────────────┐
              │ • IoU + Centroid Association │
              │ • Duplicate Frame Suppressor│
              └──────────────┬──────────────┘
                             │
                             ▼
              DETERMINISTIC ENGINE LAYER
              ┌─────────────────────────────┐
              │ • Multi-Factor Severity     │
              │ • Vehicle Risk Score (0-100)│
              │ • Road Condition Score      │
              │ • Geospatial Hotspots       │
              │ • Maintenance Priority Rank │
              └──────────────┬──────────────┘
                             │
                             ▼
              SMART CITY CONTROL CENTER & GIS
       ┌─────────────────────┼─────────────────────┐
       ▼                     ▼                     ▼
Interactive Map       Admin Dashboard       AI Inspector Assistant
(Leaflet + Clusters)  (KPIs & Chart.js)     (Database-Grounded)
```

---

## 🚦 2. Key Capabilities & Architecture

### A. Supported Road Hazard Classes (15 Categories)
- **Primary Hazards (7)**: Potholes, Speed Breakers / Bumps, Road Surface Cracks, Open Manholes, Road Debris, Waterlogging / Flooding, Damaged Road Surface.
- **Advanced Civil Hazards (8)**: Fallen Trees, Construction Obstructions, Broken Road Dividers, Missing Traffic Signs, Damaged Signals, Pavement Shoulder Damage, Exposed Drainage, Mud/Sludge.

### B. Deterministic Severity & Risk Engines
- **Separation of AI from Calculation**: The computer vision model performs defect localization and feature extraction. Mathematical scoring is computed deterministically in backend code:
  - **Severity Engine**: Evaluates Base Class Weight (45%), Relative Bounding Box Size (30%), Lane Position / Wheel Path Exposure (20%), and Water Presence (15%).
  - **Risk Engine (0–100 Score)**: Computes `Risk Score = Severity (45%) + Impact Potential (30%) + Trajectory (15%) + Citizen Recurrence (10%)` and classifies Vehicle Risk (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
  - **Explainability**: Outputs concise natural language explanations (e.g., *"Pothole surface depression (88% severity) situated in direct wheel travel path. Reported 4 times by citizen drivers."*).

### C. Multi-Frame Tracking & Duplicate Suppression
- **SORT / IoU Tracking**: Tracks physical defects across video frames (e.g. `Pothole #12` across frames 2–5) to prevent duplicate count inflation.
- **Geospatial Duplicate Matcher**: Uses Haversine great-circle distance (18m radius) to merge repeated citizen reports, increment confirmation volume, and elevate review urgency.

### D. Road Condition Score & Hotspot Detection
- **RoadGuard AI Condition Score (0–100)**: Evaluates road segments (e.g. *Grand Central Arterial Express: 42/100 "Critical Condition"*).
- **Geospatial Hotspots**: Density clustering calculates defects per kilometer and generates targeted municipal repair recommendations.

### E. Operational Roles & Workflows
1. **Public Citizen**: Photo upload, auto-GPS geolocation, instant AI verification preview.
2. **Authority / Admin**: Executive KPI control room, interactive Leaflet map, maintenance priority queue, report export (CSV/JSON/PDF), AI model evaluation.
3. **Field Inspector**: Assigned repair tasks, GPS navigation route, repair log submission with interactive **Before/After split comparison slider**.

### F. AI Road Inspector Assistant
- Grounded strictly in controlled database tools (`get_hazards`, `get_statistics`, `get_hotspots`, `get_maintenance_priority`, `get_road_condition`). Never hallucinates numbers.

---

## 🛠️ 3. Technology Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy ORM, SQLite / PostgreSQL with PostGIS compatibility, Pydantic v2, Pillow, NumPy, PyJWT, Passlib (Bcrypt).
- **Frontend**: Vanilla ES6+ Modular Single Page Application, Leaflet.js for GIS mapping, Chart.js for analytics, HTML5 Canvas for real-time HUD annotations, Web Audio API for safety alerts.
- **Machine Learning**: YOLOv8/v11 architecture, BiFPN neck, adverse weather data augmentation (rain, fog, night headlights), mAP@50 evaluation framework.

---

## 🚀 4. Quick Start & Local Execution

### Prerequisites
- Python 3.10+ / 3.11+
- Fast package manager `uv` or standard `pip`

### Step 1: Clone & Setup Virtual Environment
```bash
cd roadguard-ai
uv venv .venv
.venv\Scripts\activate   # Windows
# or: source .venv/bin/activate (Linux/macOS)
```

### Step 2: Install Dependencies
```bash
uv pip install fastapi "uvicorn[standard]" pydantic sqlalchemy python-multipart pillow numpy pytest httpx jinja2 bcrypt pyjwt passlib
```

### Step 3: Run Automated Test Suite
```bash
python -m pytest backend/tests -v
```

### Step 4: Start the Application Server
```bash
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

Open your browser at:
👉 **`http://127.0.0.1:8000`**

Interactive Swagger API Documentation:
👉 **`http://127.0.0.1:8000/docs`**

---

## 🧪 5. Testing & Verification

The test suite includes 12 automated unit and integration tests covering:
- Deterministic Severity & Risk formulas
- Monocular depth & physical sizing geometry
- Multi-frame IoU tracking & persistent ID assignment
- Haversine distance spatial calculations
- Authentication, Hazard lifecycle status transitions, and AI Assistant tool execution.

---

## 📱 6. Edge AI Deployment Architecture

For deployment on NVIDIA Jetson Orin Nano, Raspberry Pi 5, or mobile smartphones:
1. **Model Export**: Export YOLO weights to ONNX with FP16 or INT8 quantization (`yolo export format=onnx int8=True`).
2. **Edge Runtime**: Execute on-device using ONNX Runtime or TensorRT.
3. **Payload Sync**: The edge device transmits only detection metadata (`[class, confidence, bbox, GPS, timestamp]`) and compressed snapshot crops via REST API, conserving cellular bandwidth.

---

## 📄 7. License

RoadGuard AI is released under the **MIT License**.
Built for Smart City Municipalities and Infrastructure Intelligence.
