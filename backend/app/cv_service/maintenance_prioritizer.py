from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from app.database.models import Hazard, HazardStatus, SeverityLevel, MaintenanceTask, User

def compute_maintenance_priority_score(hazard: Hazard) -> float:
    """
    Computes a deterministic priority score (0 to 100) for municipal repair prioritization.
    Factors:
    - Hazard Risk Score (40%)
    - Severity Tier Bonus (25%)
    - Duplicate Citizen Report Volume (15%)
    - Age/Days Unresolved (10%)
    - Hazard Class Urgency (10%)
    """
    # 1. Base Risk Score (40 max)
    risk_part = (hazard.risk_score / 100.0) * 40.0
    
    # 2. Severity Tier Bonus (25 max)
    severity_bonus = {
        SeverityLevel.CRITICAL: 25.0,
        SeverityLevel.HIGH: 18.0,
        SeverityLevel.MEDIUM: 10.0,
        SeverityLevel.LOW: 4.0
    }.get(hazard.severity, 8.0)
    
    # 3. Duplicate Citizen Reports (15 max)
    report_vol = hazard.duplicate_count or 1
    report_bonus = min(15.0, (report_vol - 1) * 3.0 + 3.0)
    
    # 4. Aging factor (10 max)
    days_open = 0
    if hazard.detected_at:
        delta = datetime.utcnow() - hazard.detected_at
        days_open = max(0, delta.days)
    aging_bonus = min(10.0, days_open * 1.5)
    
    # 5. Class Urgency (10 max)
    norm_type = hazard.type.lower().replace(" ", "_")
    class_urgency = {
        "open_manhole": 10.0,
        "fallen_tree": 10.0,
        "pothole": 8.0,
        "broken_divider": 7.0,
        "waterlogging": 7.0,
        "damaged_surface": 6.0,
        "construction_obstruction": 6.0,
        "road_crack": 4.0
    }.get(norm_type, 5.0)
    
    total_score = risk_part + severity_bonus + report_bonus + aging_bonus + class_urgency
    return round(min(100.0, max(5.0, total_score)), 1)

def get_ranked_maintenance_queue(db: Session) -> List[Dict[str, Any]]:
    """
    Returns prioritized maintenance task list sorted strictly by computed priority score.
    """
    unresolved_hazards = db.query(Hazard).filter(
        Hazard.status.in_([
            HazardStatus.DETECTED,
            HazardStatus.REVIEW_REQUIRED,
            HazardStatus.VERIFIED,
            HazardStatus.ASSIGNED,
            HazardStatus.IN_PROGRESS,
            HazardStatus.REOPENED
        ])
    ).all()
    
    ranked_list = []
    for h in unresolved_hazards:
        score = compute_maintenance_priority_score(h)
        task = h.maintenance_task
        inspector_name = task.assigned_inspector.full_name if (task and task.assigned_inspector) else "Unassigned"
        
        ranked_list.append({
            "hazard_id": h.id,
            "type": h.type,
            "severity": h.severity.value,
            "risk_score": h.risk_score,
            "priority_score": score,
            "status": h.status.value,
            "address": h.address or "Main Highway Arterial",
            "road_segment": h.road_segment,
            "detected_at": h.detected_at.isoformat() if h.detected_at else None,
            "duplicate_count": h.duplicate_count or 1,
            "image_url": h.image_url,
            "assigned_inspector": inspector_name,
            "task_id": task.id if task else None
        })
        
    ranked_list.sort(key=lambda x: x["priority_score"], reverse=True)
    
    # Assign ordinal rank
    for rank_idx, item in enumerate(ranked_list, start=1):
        item["priority_rank"] = rank_idx
        
    return ranked_list
