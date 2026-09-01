import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, Float, String, Text, DateTime, ForeignKey, Enum, Boolean, JSON
)
from sqlalchemy.orm import relationship
from app.database.db import Base

class UserRole(str, enum.Enum):
    PUBLIC = "PUBLIC"
    ADMIN = "ADMIN"
    INSPECTOR = "INSPECTOR"

class HazardStatus(str, enum.Enum):
    DETECTED = "DETECTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    VERIFIED = "VERIFIED"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    REOPENED = "REOPENED"

class SeverityLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.PUBLIC, nullable=False)
    badge_number = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    maintenance_tasks = relationship("MaintenanceTask", back_populates="assigned_inspector")
    feedback = relationship("DetectionFeedback", back_populates="user")

class Hazard(Base):
    __tablename__ = "hazards"

    id = Column(String(32), primary_key=True, index=True)  # e.g., "HZ-00128"
    type = Column(String(64), nullable=False, index=True)  # pothole, road_crack, speed_breaker, etc.
    confidence = Column(Float, nullable=False)
    severity = Column(Enum(SeverityLevel), nullable=False, index=True)
    risk_score = Column(Integer, nullable=False)  # 0 to 100
    vehicle_risk = Column(Enum(SeverityLevel), nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    
    latitude = Column(Float, nullable=False, index=True)
    longitude = Column(Float, nullable=False, index=True)
    address = Column(String(255), nullable=True)
    road_segment = Column(String(128), nullable=True, index=True)
    
    status = Column(Enum(HazardStatus), default=HazardStatus.DETECTED, index=True)
    duplicate_count = Column(Integer, default=1)
    
    image_url = Column(String(512), nullable=True)
    depth_map_url = Column(String(512), nullable=True)
    after_image_url = Column(String(512), nullable=True)
    
    physical_dimensions = Column(JSON, nullable=True)  # {"estimated_width_cm": 62, "estimated_area_sqcm": 2400, "is_calibrated": False}
    explainability = Column(JSON, nullable=True)       # {"primary_reason": "...", "factors": [...]}
    bounding_box = Column(JSON, nullable=True)         # {"x1": 120, "y1": 180, "x2": 460, "y2": 390}
    
    model_version = Column(String(64), default="RoadGuard-YOLO-v2.4")
    notes = Column(Text, nullable=True)
    
    detected_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    detections = relationship("HazardDetection", back_populates="hazard", cascade="all, delete-orphan")
    maintenance_task = relationship("MaintenanceTask", back_populates="hazard", uselist=False)
    feedback_records = relationship("DetectionFeedback", back_populates="hazard")

class HazardDetection(Base):
    __tablename__ = "hazard_detections"

    id = Column(Integer, primary_key=True, index=True)
    hazard_id = Column(String(32), ForeignKey("hazards.id"), nullable=False)
    frame_number = Column(Integer, default=0)
    tracking_id = Column(Integer, nullable=True)
    class_name = Column(String(64), nullable=False)
    confidence = Column(Float, nullable=False)
    
    bbox_x1 = Column(Float, nullable=False)
    bbox_y1 = Column(Float, nullable=False)
    bbox_x2 = Column(Float, nullable=False)
    bbox_y2 = Column(Float, nullable=False)
    relative_area = Column(Float, nullable=True)

    hazard = relationship("Hazard", back_populates="detections")

class MaintenanceTask(Base):
    __tablename__ = "maintenance_tasks"

    id = Column(String(32), primary_key=True, index=True)  # e.g., "TASK-082"
    hazard_id = Column(String(32), ForeignKey("hazards.id"), unique=True, nullable=False)
    assigned_inspector_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    priority_score = Column(Float, nullable=False)  # Deterministic 0-100 composite ranking
    priority_rank = Column(Integer, nullable=True)
    
    status = Column(String(32), default="PENDING")  # PENDING, ASSIGNED, IN_PROGRESS, COMPLETED
    scheduled_date = Column(DateTime, nullable=True)
    completed_date = Column(DateTime, nullable=True)
    
    repair_notes = Column(Text, nullable=True)
    materials_used = Column(String(255), nullable=True)
    estimated_cost = Column(Float, nullable=True)

    hazard = relationship("Hazard", back_populates="maintenance_task")
    assigned_inspector = relationship("User", back_populates="maintenance_tasks")

class RoadConditionScore(Base):
    __tablename__ = "road_condition_scores"

    id = Column(Integer, primary_key=True, index=True)
    road_name = Column(String(128), unique=True, index=True, nullable=False)
    district = Column(String(128), nullable=False)
    
    score = Column(Integer, nullable=False)  # 0 to 100 (100 = perfect, <50 = dangerous)
    condition_label = Column(String(64), nullable=False)  # "Excellent", "Fair", "Needs Attention", "Critical"
    
    length_km = Column(Float, nullable=False, default=5.0)
    hazard_density_per_km = Column(Float, nullable=False, default=0.0)
    total_hazards = Column(Integer, default=0)
    critical_hazards = Column(Integer, default=0)
    unresolved_hazards = Column(Integer, default=0)
    
    latitude_start = Column(Float, nullable=False)
    longitude_start = Column(Float, nullable=False)
    latitude_end = Column(Float, nullable=False)
    longitude_end = Column(Float, nullable=False)
    
    last_inspected = Column(DateTime, default=datetime.utcnow)

class DetectionFeedback(Base):
    __tablename__ = "detection_feedback"

    id = Column(Integer, primary_key=True, index=True)
    hazard_id = Column(String(32), ForeignKey("hazards.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    feedback_type = Column(String(32), nullable=False)  # CORRECT, FALSE_POSITIVE, WRONG_CLASS, DUPLICATE, UNCLEAR
    suggested_class = Column(String(64), nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    hazard = relationship("Hazard", back_populates="feedback_records")
    user = relationship("User", back_populates="feedback")

class AIModelVersion(Base):
    __tablename__ = "ai_model_versions"

    id = Column(Integer, primary_key=True, index=True)
    version_name = Column(String(64), unique=True, nullable=False)
    architecture = Column(String(64), default="YOLOv8 + Feature Pyramid")
    mAP50 = Column(Float, nullable=False)
    precision = Column(Float, nullable=False)
    recall = Column(Float, nullable=False)
    f1_score = Column(Float, nullable=False)
    
    inference_latency_ms = Column(Float, default=18.5)
    fps = Column(Float, default=54.0)
    dataset_version = Column(String(32), default="RoadGuard-v2.1 (45,000 frames)")
    is_active = Column(Boolean, default=False)
    training_date = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(255), nullable=True)
    action = Column(String(64), nullable=False)  # HAZARD_DETECTED, VERIFIED, STATUS_CHANGED, ASSIGNED, REPAIRED
    target_type = Column(String(32), nullable=False)
    target_id = Column(String(64), nullable=False)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
