import math
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.database.models import Hazard, HazardStatus, SeverityLevel
from app.config import settings

def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes accurate great-circle distance between two GPS points in meters.
    """
    R = 6371000.0  # Earth radius in meters
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    
    return R * c

def find_duplicate_hazard(
    db: Session,
    hazard_type: str,
    latitude: float,
    longitude: float,
    max_distance_meters: Optional[float] = None
) -> Tuple[Optional[Hazard], float]:
    """
    Scans recent unresolved hazards of same or compatible type within proximity radius.
    Returns (matched_hazard, distance_meters) or (None, -1.0).
    """
    radius = max_distance_meters or settings.DUPLICATE_DISTANCE_METERS
    norm_type = hazard_type.lower().replace(" ", "_")
    
    # Bounding box rough filter for efficiency (~0.001 deg ~ 111m)
    deg_delta = radius / 111000.0 * 2.0
    
    candidates = db.query(Hazard).filter(
        Hazard.latitude.between(latitude - deg_delta, latitude + deg_delta),
        Hazard.longitude.between(longitude - deg_delta, longitude + deg_delta),
        Hazard.status.in_([
            HazardStatus.DETECTED, 
            HazardStatus.REVIEW_REQUIRED, 
            HazardStatus.VERIFIED, 
            HazardStatus.ASSIGNED, 
            HazardStatus.IN_PROGRESS,
            HazardStatus.REOPENED
        ])
    ).all()
    
    best_match = None
    min_dist = float("inf")
    
    for candidate in candidates:
        cand_type = candidate.type.lower().replace(" ", "_")
        # Direct class match or closely related surface fault
        type_compatible = (
            cand_type == norm_type or 
            (cand_type in ["pothole", "damaged_surface"] and norm_type in ["pothole", "damaged_surface"])
        )
        
        if not type_compatible:
            continue
            
        dist = haversine_distance_meters(latitude, longitude, candidate.latitude, candidate.longitude)
        if dist <= radius and dist < min_dist:
            min_dist = dist
            best_match = candidate
            
    if best_match:
        return best_match, round(min_dist, 1)
    return None, -1.0

def merge_duplicate_report(
    db: Session,
    existing_hazard: Hazard,
    new_confidence: float,
    new_image_url: Optional[str] = None
) -> Hazard:
    """
    Merges duplicate report into the existing hazard record, updating confirmation count and timestamps.
    """
    existing_hazard.duplicate_count = (existing_hazard.duplicate_count or 1) + 1
    existing_hazard.confidence = round(max(existing_hazard.confidence, new_confidence), 2)
    existing_hazard.updated_at = datetime.utcnow()
    
    # If 3 or more independent reports received, escalate review status
    if existing_hazard.duplicate_count >= 3 and existing_hazard.status == HazardStatus.DETECTED:
        existing_hazard.status = HazardStatus.REVIEW_REQUIRED
        
    db.commit()
    db.refresh(existing_hazard)
    return existing_hazard
