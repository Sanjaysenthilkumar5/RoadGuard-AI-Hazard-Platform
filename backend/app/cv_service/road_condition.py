from typing import List, Dict, Any
import math
from sqlalchemy.orm import Session
from app.database.models import Hazard, HazardStatus, SeverityLevel, RoadConditionScore
from app.cv_service.duplicate_filter import haversine_distance_meters

def calculate_road_condition_score(
    hazards: List[Hazard],
    length_km: float = 5.0
) -> Dict[str, Any]:
    """
    Computes deterministic RoadGuard AI Condition Score (0 to 100).
    100 = Pristine road, <40 = Critical danger.
    """
    if not hazards:
        return {
            "score": 96,
            "condition_label": "Excellent",
            "hazard_density_per_km": 0.0,
            "total_hazards": 0,
            "critical_hazards": 0,
            "unresolved_hazards": 0,
            "recommendation": "Road segment is in pristine operational condition."
        }
        
    unresolved = [h for h in hazards if h.status != HazardStatus.RESOLVED]
    total_count = len(hazards)
    unresolved_count = len(unresolved)
    
    # Hazard counts by severity
    critical_count = sum(1 for h in unresolved if h.severity == SeverityLevel.CRITICAL)
    high_count = sum(1 for h in unresolved if h.severity == SeverityLevel.HIGH)
    med_count = sum(1 for h in unresolved if h.severity == SeverityLevel.MEDIUM)
    low_count = sum(1 for h in unresolved if h.severity == SeverityLevel.LOW)
    
    # Hazard Density per KM
    density = round(unresolved_count / max(0.5, length_km), 2)
    
    # Penalty calculation
    # Critical = -18 pts, High = -8 pts, Med = -3 pts, Low = -1 pt, Density penalty
    penalty = (critical_count * 18.0) + (high_count * 8.0) + (med_count * 3.0) + (low_count * 1.0)
    density_penalty = min(25.0, density * 3.5)
    
    raw_score = max(5.0, 100.0 - penalty - density_penalty)
    final_score = int(round(raw_score))
    
    if final_score >= 85:
        label = "Excellent"
        rec = "Routine periodic inspection recommended."
    elif final_score >= 70:
        label = "Good"
        rec = "Minor surface wear observed; standard maintenance queue."
    elif final_score >= 50:
        label = "Needs Attention"
        rec = "Multiple medium-to-high severity hazards detected. Schedule inspection."
    else:
        label = "Critical Condition"
        rec = "HIGH HAZARD DENSITY: Immediate emergency maintenance intervention required."
        
    return {
        "score": final_score,
        "condition_label": label,
        "hazard_density_per_km": density,
        "total_hazards": total_count,
        "critical_hazards": critical_count,
        "high_hazards": high_count,
        "medium_hazards": med_count,
        "low_hazards": low_count,
        "unresolved_hazards": unresolved_count,
        "recommendation": rec
    }

def detect_geospatial_hotspots(
    db: Session,
    cluster_radius_meters: float = 350.0,
    min_hazards_for_hotspot: int = 3
) -> List[Dict[str, Any]]:
    """
    Geospatial clustering algorithm that groups unresolved hazards into actionable hotspots.
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
    
    if not unresolved_hazards:
        return []
        
    clusters = []
    visited_ids = set()
    
    for h in unresolved_hazards:
        if h.id in visited_ids:
            continue
            
        # Form cluster around this hazard center
        current_cluster = [h]
        visited_ids.add(h.id)
        
        for other in unresolved_hazards:
            if other.id in visited_ids:
                continue
            dist = haversine_distance_meters(h.latitude, h.longitude, other.latitude, other.longitude)
            if dist <= cluster_radius_meters:
                current_cluster.append(other)
                visited_ids.add(other.id)
                
        if len(current_cluster) >= min_hazards_for_hotspot:
            avg_lat = sum(x.latitude for x in current_cluster) / len(current_cluster)
            avg_lng = sum(x.longitude for x in current_cluster) / len(current_cluster)
            
            crit = sum(1 for x in current_cluster if x.severity == SeverityLevel.CRITICAL)
            high = sum(1 for x in current_cluster if x.severity == SeverityLevel.HIGH)
            med = sum(1 for x in current_cluster if x.severity == SeverityLevel.MEDIUM)
            low = sum(1 for x in current_cluster if x.severity == SeverityLevel.LOW)
            
            max_risk = max(x.risk_score for x in current_cluster)
            area_name = current_cluster[0].road_segment or current_cluster[0].address or "Urban Corridor Zone"
            
            # Hotspot risk rating
            hotspot_score = int(min(100, crit * 25 + high * 12 + med * 5 + len(current_cluster) * 4))
            
            clusters.append({
                "id": f"HOTSPOT-{len(clusters)+1:03d}",
                "area_name": area_name,
                "center_latitude": round(avg_lat, 6),
                "center_longitude": round(avg_lng, 6),
                "radius_meters": cluster_radius_meters,
                "total_hazards": len(current_cluster),
                "critical_count": crit,
                "high_count": high,
                "medium_count": med,
                "low_count": low,
                "max_risk_score": max_risk,
                "hotspot_risk_score": hotspot_score,
                "hazard_ids": [x.id for x in current_cluster],
                "ai_recommendation": (
                    f"Prioritize immediate road-crew deployment to {area_name}. "
                    f"Concentration of {crit} critical and {high} high-risk hazards detected."
                )
            })
            
    # Sort clusters descending by risk score
    clusters.sort(key=lambda x: x["hotspot_risk_score"], reverse=True)
    return clusters
