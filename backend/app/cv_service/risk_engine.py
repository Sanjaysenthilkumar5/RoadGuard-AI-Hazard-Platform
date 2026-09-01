from typing import Dict, Any, Tuple
from app.database.models import SeverityLevel

def calculate_risk(
    hazard_type: str,
    severity_level: SeverityLevel,
    severity_score: float,
    factors: Dict[str, Any],
    duplicate_count: int = 1,
    traffic_context: str = "URBAN_ARTERIAL"
) -> Tuple[int, SeverityLevel, Dict[str, Any]]:
    """
    Deterministic Road & Vehicle Risk Engine.
    Combines severity, road position exposure, hazard dynamics, and report recurrence.
    Returns (risk_score_0_100, vehicle_risk_level, explainability_dict).
    """
    norm_type = hazard_type.lower().replace(" ", "_")
    
    # 1. Base severity component (45% weight)
    severity_contrib = severity_score * 0.45
    
    # 2. Vehicle Dynamics Impact (30% weight)
    # Different hazards pose different threats to steering, suspension, and tire blowout
    hazard_impact_multipliers = {
        "open_manhole": 30.0,
        "fallen_tree": 28.0,
        "pothole": 24.0,
        "broken_divider": 22.0,
        "damaged_surface": 20.0,
        "construction_obstruction": 20.0,
        "waterlogging": 18.0,
        "exposed_drainage": 16.0,
        "speed_breaker": 12.0,
        "road_debris": 12.0,
        "road_crack": 8.0,
        "mud_sludge": 10.0,
        "shoulder_damage": 8.0,
        "damaged_signal": 14.0,
        "missing_sign": 6.0
    }
    impact_contrib = hazard_impact_multipliers.get(norm_type, 15.0)
    
    # 3. Position & Exposure (15% weight)
    position_contrib = 15.0 if factors.get("is_in_vehicle_wheel_path", False) else 5.0
    
    # 4. Citizen Recurrence Boost (10% weight)
    # Repeated unaddressed reports signify an active deteriorating hazard
    recurrence_contrib = min(10.0, (duplicate_count - 1) * 3.0)
    
    # Raw composite score (0 to 100)
    raw_risk = severity_contrib + impact_contrib + position_contrib + recurrence_contrib
    final_risk_score = int(min(100, max(1, round(raw_risk))))
    
    # Vehicle Risk Classification
    if final_risk_score >= 80:
        vehicle_risk = SeverityLevel.CRITICAL
    elif final_risk_score >= 60:
        vehicle_risk = SeverityLevel.HIGH
    elif final_risk_score >= 40:
        vehicle_risk = SeverityLevel.MEDIUM
    else:
        vehicle_risk = SeverityLevel.LOW
        
    # Generate structured explainability
    reason_templates = {
        "open_manhole": "Unprotected open manhole creates catastrophic wheel drop and suspension failure risk.",
        "fallen_tree": "Major physical obstruction blocking travel lanes with immediate collision risk.",
        "pothole": f"Pothole surface depression ({factors.get('composite_severity_score', 0):.0f}% severity) situated in direct wheel travel path.",
        "waterlogging": "Waterlogging and standing water obscures submerged surface hazards and induces hydroplaning risk.",
        "road_crack": "Surface road crack propagating across pavement structure; potential precursor to pothole formation.",
        "speed_breaker": "Unmarked speed attenuation structure with sudden vertical deceleration impact.",
        "road_debris": "Loose foreign object on roadway posing tire puncture and swerving hazard.",
        "damaged_surface": "Extensive surface degradation causing severe traction loss and vibration.",
        "broken_divider": "Damaged lane separator creating cross-traffic encroachment danger.",
        "construction_obstruction": "Work zone debris and barricades encroaching on active transit lanes."
    }
    
    primary_reason = reason_templates.get(
        norm_type, 
        f"Detected {hazard_type} with {final_risk_score}/100 composite risk rating."
    )
    
    if duplicate_count > 1:
        primary_reason += f" Reported {duplicate_count} times by citizen drivers."
        
    explainability = {
        "risk_score": final_risk_score,
        "vehicle_risk_level": vehicle_risk.value,
        "primary_reason": primary_reason,
        "contributing_factors": [
            {"factor": "Hazard Severity", "points": round(severity_contrib, 1), "max": 45},
            {"factor": "Vehicle Impact Potential", "points": round(impact_contrib, 1), "max": 30},
            {"factor": "Wheel Path Trajectory", "points": round(position_contrib, 1), "max": 15},
            {"factor": "Citizen Confirmation Recurrence", "points": round(recurrence_contrib, 1), "max": 10}
        ],
        "advisory": (
            "CRITICAL: Immediate deceleration recommended; high risk of vehicle damage."
            if vehicle_risk == SeverityLevel.CRITICAL
            else "Caution: Reduce speed and maintain lane vigilance."
        )
    }
    
    return final_risk_score, vehicle_risk, explainability
