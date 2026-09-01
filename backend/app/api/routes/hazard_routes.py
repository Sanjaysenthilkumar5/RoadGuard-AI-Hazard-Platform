from typing import Optional, List
from datetime import datetime
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database.db import get_db
from app.database.models import (
    Hazard, HazardStatus, SeverityLevel, User, UserRole, 
    DetectionFeedback, MaintenanceTask, AuditLog
)
from app.auth.dependencies import get_current_user, require_admin, require_inspector_or_admin

router = APIRouter(prefix="/hazards", tags=["Hazards Management"])

class HazardCreateRequest(BaseModel):
    type: str
    confidence: float = 0.90
    severity: SeverityLevel = SeverityLevel.MEDIUM
    risk_score: int = 50
    vehicle_risk: SeverityLevel = SeverityLevel.MEDIUM
    latitude: float
    longitude: float
    address: Optional[str] = None
    road_segment: Optional[str] = None
    image_url: Optional[str] = None
    notes: Optional[str] = None

class HazardStatusUpdateRequest(BaseModel):
    status: HazardStatus
    notes: Optional[str] = None

class HazardFeedbackRequest(BaseModel):
    feedback_type: str  # CORRECT, FALSE_POSITIVE, WRONG_CLASS, DUPLICATE, UNCLEAR
    suggested_class: Optional[str] = None
    comment: Optional[str] = None

@router.get("")
def list_hazards(
    severity: Optional[SeverityLevel] = None,
    type: Optional[str] = None,
    status: Optional[HazardStatus] = None,
    road_segment: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = Query("risk_score", pattern="^(risk_score|detected_at|severity|confidence)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    query = db.query(Hazard)
    
    if severity:
        query = query.filter(Hazard.severity == severity)
    if type:
        query = query.filter(Hazard.type.ilike(f"%{type}%"))
    if status:
        query = query.filter(Hazard.status == status)
    if road_segment:
        query = query.filter(Hazard.road_segment.ilike(f"%{road_segment}%"))
    if search:
        query = query.filter(
            (Hazard.id.ilike(f"%{search}%")) |
            (Hazard.type.ilike(f"%{search}%")) |
            (Hazard.address.ilike(f"%{search}%")) |
            (Hazard.road_segment.ilike(f"%{search}%"))
        )
        
    order_col = getattr(Hazard, sort_by, Hazard.risk_score)
    if sort_order == "desc":
        query = query.order_by(desc(order_col))
    else:
        query = query.order_by(order_col)
        
    total = query.count()
    hazards = query.offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "count": len(hazards),
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": h.id,
                "type": h.type,
                "confidence": h.confidence,
                "severity": h.severity.value,
                "risk_score": h.risk_score,
                "vehicle_risk": h.vehicle_risk.value,
                "latitude": h.latitude,
                "longitude": h.longitude,
                "address": h.address,
                "road_segment": h.road_segment,
                "status": h.status.value,
                "duplicate_count": h.duplicate_count,
                "image_url": h.image_url,
                "depth_map_url": h.depth_map_url,
                "after_image_url": h.after_image_url,
                "physical_dimensions": h.physical_dimensions,
                "explainability": h.explainability,
                "model_version": h.model_version,
                "detected_at": h.detected_at.isoformat() if h.detected_at else None,
                "updated_at": h.updated_at.isoformat() if h.updated_at else None
            }
            for h in hazards
        ]
    }

@router.get("/{hazard_id}")
def get_hazard_details(hazard_id: str, db: Session = Depends(get_db)):
    hazard = db.query(Hazard).filter(Hazard.id == hazard_id).first()
    if not hazard:
        raise HTTPException(status_code=404, detail="Hazard not found")
        
    task = hazard.maintenance_task
    inspector_info = None
    if task and task.assigned_inspector:
        inspector_info = {
            "id": task.assigned_inspector.id,
            "name": task.assigned_inspector.full_name,
            "badge": task.assigned_inspector.badge_number
        }
        
    return {
        "id": hazard.id,
        "type": hazard.type,
        "confidence": hazard.confidence,
        "severity": hazard.severity.value,
        "risk_score": hazard.risk_score,
        "vehicle_risk": hazard.vehicle_risk.value,
        "latitude": hazard.latitude,
        "longitude": hazard.longitude,
        "address": hazard.address,
        "road_segment": hazard.road_segment,
        "status": hazard.status.value,
        "duplicate_count": hazard.duplicate_count,
        "image_url": hazard.image_url,
        "depth_map_url": hazard.depth_map_url,
        "after_image_url": hazard.after_image_url,
        "physical_dimensions": hazard.physical_dimensions,
        "explainability": hazard.explainability,
        "bounding_box": hazard.bounding_box,
        "model_version": hazard.model_version,
        "notes": hazard.notes,
        "detected_at": hazard.detected_at.isoformat() if hazard.detected_at else None,
        "updated_at": hazard.updated_at.isoformat() if hazard.updated_at else None,
        "maintenance_task": {
            "task_id": task.id,
            "priority_score": task.priority_score,
            "priority_rank": task.priority_rank,
            "status": task.status,
            "assigned_inspector": inspector_info,
            "scheduled_date": task.scheduled_date.isoformat() if task.scheduled_date else None,
            "completed_date": task.completed_date.isoformat() if task.completed_date else None,
            "repair_notes": task.repair_notes
        } if task else None
    }

@router.post("", status_code=201)
def create_hazard(req: HazardCreateRequest, db: Session = Depends(get_db)):
    new_id = f"HZ-{uuid.uuid4().hex[:6].upper()}"
    hazard = Hazard(
        id=new_id,
        type=req.type,
        confidence=req.confidence,
        severity=req.severity,
        risk_score=req.risk_score,
        vehicle_risk=req.vehicle_risk,
        latitude=req.latitude,
        longitude=req.longitude,
        address=req.address or f"Coordinates {req.latitude:.4f}, {req.longitude:.4f}",
        road_segment=req.road_segment or "Monitored Segment",
        status=HazardStatus.DETECTED,
        image_url=req.image_url,
        notes=req.notes
    )
    db.add(hazard)
    db.commit()
    db.refresh(hazard)
    return {"id": hazard.id, "status": "CREATED"}

@router.post("/{hazard_id}/status")
def update_hazard_status(
    hazard_id: str, 
    req: HazardStatusUpdateRequest, 
    db: Session = Depends(get_db)
):
    hazard = db.query(Hazard).filter(Hazard.id == hazard_id).first()
    if not hazard:
        raise HTTPException(status_code=404, detail="Hazard not found")
        
    prev_status = hazard.status
    hazard.status = req.status
    hazard.updated_at = datetime.utcnow()
    if req.notes:
        hazard.notes = (hazard.notes or "") + f"\n[{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}] Status updated to {req.status.value}: {req.notes}"
        
    db.commit()
    db.refresh(hazard)
    return {
        "id": hazard.id,
        "previous_status": prev_status.value,
        "current_status": hazard.status.value,
        "updated_at": hazard.updated_at.isoformat()
    }

@router.post("/{hazard_id}/verify")
def verify_hazard(hazard_id: str, db: Session = Depends(get_db)):
    hazard = db.query(Hazard).filter(Hazard.id == hazard_id).first()
    if not hazard:
        raise HTTPException(status_code=404, detail="Hazard not found")
        
    hazard.status = HazardStatus.VERIFIED
    hazard.updated_at = datetime.utcnow()
    db.commit()
    return {"id": hazard.id, "status": HazardStatus.VERIFIED.value}

@router.post("/{hazard_id}/feedback")
def submit_detection_feedback(
    hazard_id: str, 
    req: HazardFeedbackRequest, 
    db: Session = Depends(get_db)
):
    hazard = db.query(Hazard).filter(Hazard.id == hazard_id).first()
    if not hazard:
        raise HTTPException(status_code=404, detail="Hazard not found")
        
    feedback = DetectionFeedback(
        hazard_id=hazard.id,
        feedback_type=req.feedback_type,
        suggested_class=req.suggested_class,
        comment=req.comment
    )
    db.add(feedback)
    
    # If flagged as false positive, adjust review status
    if req.feedback_type == "FALSE_POSITIVE":
        hazard.status = HazardStatus.REVIEW_REQUIRED
        
    db.commit()
    return {"status": "FEEDBACK_RECORDED", "feedback_type": req.feedback_type}
