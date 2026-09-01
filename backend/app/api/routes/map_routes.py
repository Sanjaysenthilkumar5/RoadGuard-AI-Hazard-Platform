from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.database.models import Hazard, HazardStatus, SeverityLevel, RoadConditionScore
from app.cv_service.road_condition import detect_geospatial_hotspots

router = APIRouter(prefix="/map", tags=["Interactive Map & Geospatial"])

@router.get("/hazards")
def get_map_hazards(
    severity: Optional[SeverityLevel] = None,
    type: Optional[str] = None,
    status: Optional[HazardStatus] = None,
    unresolved_only: bool = False,
    db: Session = Depends(get_db)
):
    """
    Returns structured GeoJSON-compatible points for Leaflet map markers.
    """
    query = db.query(Hazard)
    if severity:
        query = query.filter(Hazard.severity == severity)
    if type:
        query = query.filter(Hazard.type.ilike(f"%{type}%"))
    if status:
        query = query.filter(Hazard.status == status)
    if unresolved_only:
        query = query.filter(Hazard.status != HazardStatus.RESOLVED)
        
    hazards = query.all()
    
    features = []
    for h in hazards:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [h.longitude, h.latitude]
            },
            "properties": {
                "id": h.id,
                "type": h.type,
                "confidence": h.confidence,
                "severity": h.severity.value,
                "risk_score": h.risk_score,
                "vehicle_risk": h.vehicle_risk.value,
                "status": h.status.value,
                "address": h.address,
                "road_segment": h.road_segment,
                "duplicate_count": h.duplicate_count,
                "image_url": h.image_url,
                "after_image_url": h.after_image_url,
                "detected_at": h.detected_at.strftime("%Y-%m-%d %H:%M") if h.detected_at else "Recent"
            }
        })
        
    return {
        "type": "FeatureCollection",
        "count": len(features),
        "features": features
    }

@router.get("/hotspots")
def get_hotspots(
    radius_meters: float = Query(350.0, ge=50, le=2000),
    min_hazards: int = Query(3, ge=2, le=20),
    db: Session = Depends(get_db)
):
    """
    Returns high-density hazard concentration zones for heat overlays and warning circles.
    """
    hotspots = detect_geospatial_hotspots(db, cluster_radius_meters=radius_meters, min_hazards_for_hotspot=min_hazards)
    return {
        "count": len(hotspots),
        "hotspots": hotspots
    }

@router.get("/road-conditions")
def get_road_conditions(db: Session = Depends(get_db)):
    """
    Returns municipal road segment segments with computed RoadGuard Condition Scores.
    """
    segments = db.query(RoadConditionScore).all()
    return [
        {
            "id": s.id,
            "road_name": s.road_name,
            "district": s.district,
            "score": s.score,
            "condition_label": s.condition_label,
            "length_km": s.length_km,
            "hazard_density_per_km": s.hazard_density_per_km,
            "total_hazards": s.total_hazards,
            "critical_hazards": s.critical_hazards,
            "unresolved_hazards": s.unresolved_hazards,
            "coordinates": {
                "start": [s.latitude_start, s.longitude_start],
                "end": [s.latitude_end, s.longitude_end]
            }
        }
        for s in segments
    ]
