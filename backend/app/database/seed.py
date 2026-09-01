import os
import io
import base64
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFilter
from sqlalchemy.orm import Session

from app.database.db import engine, SessionLocal, Base
from app.database.models import (
    User, UserRole, Hazard, HazardStatus, SeverityLevel, 
    MaintenanceTask, RoadConditionScore, AIModelVersion, DetectionFeedback
)
from app.auth.security import get_password_hash
from app.cv_service.size_depth_estimator import generate_relative_depth_map
from app.cv_service.maintenance_prioritizer import compute_maintenance_priority_score

def create_sample_road_image(hazard_type: str, severity: str) -> str:
    """
    Synthesizes a high-fidelity synthetic dashcam road texture with the specified defect drawn on it.
    Returns base64 JPEG data URL.
    """
    w, h = 640, 400
    img = Image.new("RGB", (w, h), "#334155")
    draw = ImageDraw.Draw(img)
    
    # Draw asphalt road perspective
    draw.polygon([(0, h), (w, h), (int(w * 0.7), int(h * 0.4)), (int(w * 0.3), int(h * 0.4))], fill="#1e293b")
    # Draw sky / horizon
    draw.rectangle([(0, 0), (w, int(h * 0.4))], fill="#0f172a")
    
    # Draw lane divider lines
    draw.line([(int(w * 0.5), int(h * 0.4)), (int(w * 0.5), h)], fill="#e2e8f0", width=4)
    draw.line([(int(w * 0.35), int(h * 0.4)), (int(w * 0.05), h)], fill="#fbbf24", width=3)
    draw.line([(int(w * 0.65), int(h * 0.4)), (int(w * 0.95), h)], fill="#fbbf24", width=3)

    # Draw specific hazard morphology
    if hazard_type == "pothole":
        draw.ellipse([(int(w*0.38), int(h*0.62)), (int(w*0.62), int(h*0.82))], fill="#090d16", outline="#475569", width=3)
        draw.ellipse([(int(w*0.42), int(h*0.66)), (int(w*0.58), int(h*0.78))], fill="#020617")
    elif hazard_type == "open_manhole":
        draw.ellipse([(int(w*0.42), int(h*0.65)), (int(w*0.58), int(h*0.80))], fill="#000000", outline="#ef4444", width=4)
    elif hazard_type == "waterlogging":
        draw.polygon([(int(w*0.25), int(h*0.70)), (int(w*0.75), int(h*0.70)), (int(w*0.85), int(h*0.92)), (int(w*0.15), int(h*0.92))], fill="#0369a1")
    elif hazard_type == "road_crack":
        points = [(int(w*0.35), int(h*0.58)), (int(w*0.42), int(h*0.68)), (int(w*0.50), int(h*0.72)), (int(w*0.65), int(h*0.88))]
        draw.line(points, fill="#0f172a", width=6)
    elif hazard_type == "speed_breaker":
        draw.polygon([(int(w*0.20), int(h*0.72)), (int(w*0.80), int(h*0.72)), (int(w*0.85), int(h*0.78)), (int(w*0.15), int(h*0.78))], fill="#d97706")
        draw.line([(int(w*0.25), int(h*0.75)), (int(w*0.75), int(h*0.75))], fill="#ffffff", width=4)
    else:
        draw.ellipse([(int(w*0.40), int(h*0.65)), (int(w*0.60), int(h*0.80))], fill="#1e293b", outline="#ea580c", width=3)

    # Convert to base64
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buffered.getvalue()).decode("utf-8")

def create_sample_repaired_road_image() -> str:
    """
    Synthesizes smooth, freshly repaired asphalt texture.
    """
    w, h = 640, 400
    img = Image.new("RGB", (w, h), "#334155")
    draw = ImageDraw.Draw(img)
    
    # Asphalt road
    draw.polygon([(0, h), (w, h), (int(w * 0.7), int(h * 0.4)), (int(w * 0.3), int(h * 0.4))], fill="#0f172a")
    draw.rectangle([(0, 0), (w, int(h * 0.4))], fill="#090d16")
    
    # Pristine dark asphalt patch
    draw.ellipse([(int(w*0.35), int(h*0.60)), (int(w*0.65), int(h*0.84))], fill="#020617", outline="#1e293b", width=2)
    # Bright new lane stripes
    draw.line([(int(w * 0.5), int(h * 0.4)), (int(w * 0.5), h)], fill="#38bdf8", width=4)
    draw.line([(int(w * 0.35), int(h * 0.4)), (int(w * 0.05), h)], fill="#fbbf24", width=3)
    draw.line([(int(w * 0.65), int(h * 0.4)), (int(w * 0.95), h)], fill="#fbbf24", width=3)

    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buffered.getvalue()).decode("utf-8")

def seed_database():
    """
    Populates database with initial schema, demo users, model versions, road scores, and sample hazards.
    """
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    try:
        # Check if already seeded
        if db.query(User).count() > 0:
            print("Database already contains records. Skipping seed.")
            return

        print("Seeding RoadGuard AI demo dataset...")
        
        # 1. Users
        users = [
            User(
                email="admin@roadguard.ai",
                password_hash=get_password_hash("roadguard123"),
                full_name="Elena Vance",
                role=UserRole.ADMIN,
                badge_number="ADM-9901"
            ),
            User(
                email="inspector@roadguard.ai",
                password_hash=get_password_hash("roadguard123"),
                full_name="Marcus Stone",
                role=UserRole.INSPECTOR,
                badge_number="INSP-0042"
            ),
            User(
                email="citizen@roadguard.ai",
                password_hash=get_password_hash("roadguard123"),
                full_name="Alex Rivera",
                role=UserRole.PUBLIC,
                badge_number=None
            )
        ]
        db.add_all(users)
        db.commit()
        
        admin_user = db.query(User).filter(User.email == "admin@roadguard.ai").first()
        inspector_user = db.query(User).filter(User.email == "inspector@roadguard.ai").first()

        # 2. AI Model Versions
        models = [
            AIModelVersion(
                version_name="RoadGuard-YOLO-v1.0-MobileNet",
                architecture="YOLOv5-Nano + MobileNetV3 Backbone",
                mAP50=0.812,
                precision=0.825,
                recall=0.798,
                f1_score=0.811,
                inference_latency_ms=8.2,
                fps=110.0,
                dataset_version="RoadGuard-v1.0 (15,000 frames)",
                is_active=False
            ),
            AIModelVersion(
                version_name="RoadGuard-YOLO-v2.0-Standard",
                architecture="YOLOv8-Medium + PANet Neck",
                mAP50=0.886,
                precision=0.894,
                recall=0.871,
                f1_score=0.882,
                inference_latency_ms=12.4,
                fps=78.0,
                dataset_version="RoadGuard-v2.0 (30,000 frames)",
                is_active=False
            ),
            AIModelVersion(
                version_name="RoadGuard-YOLO-v2.4",
                architecture="YOLOv8x + BiFPN Head + Swin-Transformer",
                mAP50=0.924,
                precision=0.928,
                recall=0.904,
                f1_score=0.916,
                inference_latency_ms=14.8,
                fps=67.5,
                dataset_version="RoadGuard-v2.1 (45,000 frames)",
                is_active=True
            )
        ]
        db.add_all(models)

        # 3. Road Condition Scores
        road_segments = [
            RoadConditionScore(
                road_name="Grand Central Arterial Express",
                district="Downtown Core",
                score=42,
                condition_label="Critical Condition",
                length_km=6.2,
                hazard_density_per_km=4.8,
                total_hazards=30,
                critical_hazards=6,
                unresolved_hazards=22,
                latitude_start=37.7749,
                longitude_start=-122.4194,
                latitude_end=37.7850,
                longitude_end=-122.4050
            ),
            RoadConditionScore(
                road_name="North Bay Coastal Highway",
                district="Harbor District",
                score=68,
                condition_label="Needs Attention",
                length_km=8.5,
                hazard_density_per_km=2.1,
                total_hazards=18,
                critical_hazards=2,
                unresolved_hazards=12,
                latitude_start=37.7900,
                longitude_start=-122.4300,
                latitude_end=37.8050,
                longitude_end=-122.4200
            ),
            RoadConditionScore(
                road_name="Oakridge Boulevard",
                district="Residential West",
                score=88,
                condition_label="Excellent",
                length_km=4.0,
                hazard_density_per_km=0.5,
                total_hazards=2,
                critical_hazards=0,
                unresolved_hazards=1,
                latitude_start=37.7600,
                longitude_start=-122.4500,
                latitude_end=37.7700,
                longitude_end=-122.4400
            ),
            RoadConditionScore(
                road_name="Industrial Freight Parkway",
                district="East Logistics Corridor",
                score=54,
                condition_label="Needs Attention",
                length_km=5.0,
                hazard_density_per_km=3.4,
                total_hazards=17,
                critical_hazards=3,
                unresolved_hazards=11,
                latitude_start=37.7500,
                longitude_start=-122.3900,
                latitude_end=37.7650,
                longitude_end=-122.3800
            )
        ]
        db.add_all(road_segments)
        db.commit()

        # 4. Realistic Sample Hazards
        sample_hazards_data = [
            {
                "id": "HZ-00128",
                "type": "pothole",
                "confidence": 0.95,
                "severity": SeverityLevel.CRITICAL,
                "risk_score": 88,
                "vehicle_risk": SeverityLevel.CRITICAL,
                "latitude": 37.7762,
                "longitude": -122.4178,
                "address": "452 Market St / 5th Ave",
                "road_segment": "Grand Central Arterial Express",
                "status": HazardStatus.VERIFIED,
                "duplicate_count": 4,
                "width_cm": 68.0,
                "notes": "Large deep depression in right-hand wheel track; causes sharp suspension impact."
            },
            {
                "id": "HZ-00129",
                "type": "open_manhole",
                "confidence": 0.98,
                "severity": SeverityLevel.CRITICAL,
                "risk_score": 96,
                "vehicle_risk": SeverityLevel.CRITICAL,
                "latitude": 37.7790,
                "longitude": -122.4140,
                "address": "789 Mission St",
                "road_segment": "Grand Central Arterial Express",
                "status": HazardStatus.ASSIGNED,
                "duplicate_count": 6,
                "width_cm": 60.0,
                "notes": "Missing cast-iron sewer cover; severe wheel ingestion risk."
            },
            {
                "id": "HZ-00130",
                "type": "waterlogging",
                "confidence": 0.91,
                "severity": SeverityLevel.HIGH,
                "risk_score": 74,
                "vehicle_risk": SeverityLevel.HIGH,
                "latitude": 37.7820,
                "longitude": -122.4100,
                "address": "1020 Folsom St Underpass",
                "road_segment": "Grand Central Arterial Express",
                "status": HazardStatus.REVIEW_REQUIRED,
                "duplicate_count": 2,
                "width_cm": 240.0,
                "notes": "Standing water across 2 active lanes due to clogged storm drain."
            },
            {
                "id": "HZ-00131",
                "type": "road_crack",
                "confidence": 0.89,
                "severity": SeverityLevel.MEDIUM,
                "risk_score": 52,
                "vehicle_risk": SeverityLevel.MEDIUM,
                "latitude": 37.7940,
                "longitude": -122.4260,
                "address": "1200 Bay St",
                "road_segment": "North Bay Coastal Highway",
                "status": HazardStatus.DETECTED,
                "duplicate_count": 1,
                "width_cm": 120.0,
                "notes": "Transverse pavement fatigue crack propagating across westbound lane."
            },
            {
                "id": "HZ-00132",
                "type": "speed_breaker",
                "confidence": 0.93,
                "severity": SeverityLevel.MEDIUM,
                "risk_score": 46,
                "vehicle_risk": SeverityLevel.MEDIUM,
                "latitude": 37.7650,
                "longitude": -122.4450,
                "address": "250 Oakridge Blvd",
                "road_segment": "Oakridge Boulevard",
                "status": HazardStatus.VERIFIED,
                "duplicate_count": 2,
                "width_cm": 350.0,
                "notes": "Unpainted speed bump lacking reflective yellow chevron markers."
            },
            {
                "id": "HZ-00133",
                "type": "damaged_surface",
                "confidence": 0.87,
                "severity": SeverityLevel.HIGH,
                "risk_score": 72,
                "vehicle_risk": SeverityLevel.HIGH,
                "latitude": 37.7550,
                "longitude": -122.3850,
                "address": "880 Freightway Terminal",
                "road_segment": "Industrial Freight Parkway",
                "status": HazardStatus.IN_PROGRESS,
                "duplicate_count": 3,
                "width_cm": 180.0,
                "notes": "Extensive asphalt rutting and alligator cracking caused by heavy truck traffic."
            },
            {
                "id": "HZ-00134",
                "type": "pothole",
                "confidence": 0.94,
                "severity": SeverityLevel.HIGH,
                "risk_score": 78,
                "vehicle_risk": SeverityLevel.HIGH,
                "latitude": 37.7580,
                "longitude": -122.3880,
                "address": "920 Freightway Ave",
                "road_segment": "Industrial Freight Parkway",
                "status": HazardStatus.RESOLVED,
                "duplicate_count": 5,
                "width_cm": 55.0,
                "notes": "Repaired and compacted with hot asphalt mix by municipal road crew."
            },
            {
                "id": "HZ-00135",
                "type": "road_debris",
                "confidence": 0.84,
                "severity": SeverityLevel.LOW,
                "risk_score": 34,
                "vehicle_risk": SeverityLevel.LOW,
                "latitude": 37.7680,
                "longitude": -122.4410,
                "address": "400 Oakridge Blvd",
                "road_segment": "Oakridge Boulevard",
                "status": HazardStatus.RESOLVED,
                "duplicate_count": 1,
                "width_cm": 40.0,
                "notes": "Loose wooden pallet removed by highway patrol."
            }
        ]

        repaired_img_url = create_sample_repaired_road_image()

        for h_data in sample_hazards_data:
            img_b64 = create_sample_road_image(h_data["type"], h_data["severity"].value)
            
            hazard = Hazard(
                id=h_data["id"],
                type=h_data["type"],
                confidence=h_data["confidence"],
                severity=h_data["severity"],
                risk_score=h_data["risk_score"],
                vehicle_risk=h_data["vehicle_risk"],
                latitude=h_data["latitude"],
                longitude=h_data["longitude"],
                address=h_data["address"],
                road_segment=h_data["road_segment"],
                status=h_data["status"],
                duplicate_count=h_data["duplicate_count"],
                image_url=img_b64,
                after_image_url=repaired_img_url if h_data["status"] == HazardStatus.RESOLVED else None,
                bounding_box={"x1": 240, "y1": 250, "x2": 400, "y2": 330},
                physical_dimensions={
                    "estimated_width_cm": h_data["width_cm"],
                    "estimated_length_cm": round(h_data["width_cm"] * 0.85, 1),
                    "estimated_area_sqcm": round(h_data["width_cm"] * h_data["width_cm"] * 0.85, 0),
                    "is_calibrated": False,
                    "measurement_disclaimer": "Approximate relative size estimated via perspective geometry."
                },
                explainability={
                    "risk_score": h_data["risk_score"],
                    "vehicle_risk_level": h_data["vehicle_risk"].value,
                    "primary_reason": f"Detected {h_data['type']} in vehicle travel trajectory. Severity index {h_data['severity'].value}."
                },
                model_version="RoadGuard-YOLO-v2.4",
                notes=h_data["notes"],
                detected_at=datetime.utcnow() - timedelta(days=h_data.get("duplicate_count", 1) * 2)
            )
            db.add(hazard)
            db.flush()

            # Add Maintenance Task
            priority_score = compute_maintenance_priority_score(hazard)
            is_resolved = (h_data["status"] == HazardStatus.RESOLVED)
            
            task = MaintenanceTask(
                id=f"TASK-{h_data['id'][3:]}",
                hazard_id=hazard.id,
                assigned_inspector_id=inspector_user.id if h_data["status"] in [HazardStatus.ASSIGNED, HazardStatus.IN_PROGRESS, HazardStatus.RESOLVED] else None,
                priority_score=priority_score,
                status="COMPLETED" if is_resolved else ("ASSIGNED" if h_data["status"] == HazardStatus.ASSIGNED else "PENDING"),
                scheduled_date=datetime.utcnow() + timedelta(days=2),
                completed_date=datetime.utcnow() - timedelta(hours=6) if is_resolved else None,
                repair_notes="Asphalt concrete patch hot compacted to grade." if is_resolved else None,
                materials_used="Hot-mix Asphalt Type 3" if is_resolved else None,
                estimated_cost=380.0
            )
            db.add(task)

        db.commit()
        print("RoadGuard AI demo database seeded successfully with 8 sample hazards, 4 road segments, and 3 user roles!")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
