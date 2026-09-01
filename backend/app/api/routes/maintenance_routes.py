from typing import Optional
from datetime import datetime
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.database.models import (
    Hazard, HazardStatus, MaintenanceTask, User, UserRole, AuditLog
)
from app.cv_service.maintenance_prioritizer import get_ranked_maintenance_queue, compute_maintenance_priority_score
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/maintenance", tags=["Maintenance & Field Operations"])

class AssignTaskRequest(BaseModel):
    inspector_id: int
    scheduled_date: Optional[str] = None
    notes: Optional[str] = None

class ResolveTaskRequest(BaseModel):
    repair_notes: str
    materials_used: Optional[str] = "Hot-mix asphalt patch + seal"
    estimated_cost: Optional[float] = 350.0

@router.get("/queue")
def get_maintenance_queue(db: Session = Depends(get_db)):
    """
    Returns the deterministic prioritized maintenance task list for municipal road authority.
    """
    queue = get_ranked_maintenance_queue(db)
    return {
        "total_unresolved": len(queue),
        "queue": queue
    }

@router.get("/inspectors")
def list_field_inspectors(db: Session = Depends(get_db)):
    """
    Lists registered field inspectors and road maintenance crew leads.
    """
    inspectors = db.query(User).filter(User.role.in_([UserRole.INSPECTOR, UserRole.ADMIN])).all()
    return [
        {
            "id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "badge_number": u.badge_number or "INSP-01",
            "active_tasks_count": db.query(MaintenanceTask).filter(
                MaintenanceTask.assigned_inspector_id == u.id,
                MaintenanceTask.status.in_(["ASSIGNED", "IN_PROGRESS"])
            ).count()
        }
        for u in inspectors
    ]

@router.post("/{hazard_id}/assign")
def assign_hazard_maintenance(
    hazard_id: str,
    req: AssignTaskRequest,
    db: Session = Depends(get_db)
):
    hazard = db.query(Hazard).filter(Hazard.id == hazard_id).first()
    if not hazard:
        raise HTTPException(status_code=404, detail="Hazard not found")
        
    inspector = db.query(User).filter(User.id == req.inspector_id).first()
    if not inspector:
        raise HTTPException(status_code=404, detail="Inspector not found")
        
    task = hazard.maintenance_task
    if not task:
        task_id = f"TASK-{uuid.uuid4().hex[:5].upper()}"
        score = compute_maintenance_priority_score(hazard)
        task = MaintenanceTask(
            id=task_id,
            hazard_id=hazard.id,
            assigned_inspector_id=inspector.id,
            priority_score=score,
            status="ASSIGNED",
            scheduled_date=datetime.utcnow()
        )
        db.add(task)
    else:
        task.assigned_inspector_id = inspector.id
        task.status = "ASSIGNED"
        
    hazard.status = HazardStatus.ASSIGNED
    hazard.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    
    return {
        "status": "ASSIGNED",
        "task_id": task.id,
        "assigned_to": inspector.full_name,
        "hazard_status": hazard.status.value
    }

@router.post("/{hazard_id}/resolve")
async def resolve_hazard_maintenance(
    hazard_id: str,
    repair_notes: str = Form("Surface resurfaced and compacted with hot asphalt."),
    materials_used: str = Form("Asphalt Concrete Grade 2"),
    estimated_cost: float = Form(420.0),
    after_image: Optional[UploadFile] = File(None),
    after_image_url: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Submits repair completion evidence (after-image and maintenance log) and marks hazard RESOLVED.
    """
    hazard = db.query(Hazard).filter(Hazard.id == hazard_id).first()
    if not hazard:
        raise HTTPException(status_code=404, detail="Hazard not found")
        
    final_after_url = after_image_url
    if after_image:
        contents = await after_image.read()
        import base64
        final_after_url = "data:image/jpeg;base64," + base64.b64encode(contents).decode("utf-8")
        
    if not final_after_url:
        # Default high-quality repaired road image placeholder if no file uploaded
        final_after_url = "/static/assets/sample_repaired_road.jpg"
        
    hazard.status = HazardStatus.RESOLVED
    hazard.after_image_url = final_after_url
    hazard.updated_at = datetime.utcnow()
    
    task = hazard.maintenance_task
    if task:
        task.status = "COMPLETED"
        task.completed_date = datetime.utcnow()
        task.repair_notes = repair_notes
        task.materials_used = materials_used
        task.estimated_cost = estimated_cost
        
    db.commit()
    db.refresh(hazard)
    
    return {
        "status": "RESOLVED",
        "hazard_id": hazard.id,
        "hazard_status": hazard.status.value,
        "after_image_url": hazard.after_image_url,
        "completed_at": datetime.utcnow().isoformat()
    }
