from typing import Dict, Any, Tuple
from app.database.models import SeverityLevel

# Base severity weights by hazard class (0.0 to 1.0)
HAZARD_CLASS_BASE_WEIGHTS = {
    "open_manhole": 0.95,
    "fallen_tree": 0.90,
    "pothole": 0.75,
    "damaged_surface": 0.70,
    "construction_obstruction": 0.70,
    "waterlogging": 0.65,
    "damaged_signal": 0.65,
    "broken_divider": 0.60,
    "exposed_drainage": 0.60,
    "speed_breaker": 0.45,
    "road_debris": 0.45,
    "road_crack": 0.40,
    "mud_sludge": 0.40,
    "shoulder_damage": 0.35,
    "missing_sign": 0.30
}

def calculate_severity(
    hazard_type: str,
    confidence: float,
    relative_area_pct: float,
    bbox: Dict[str, float],
    img_width: int,
    img_height: int,
    water_detected: bool = False
) -> Tuple[SeverityLevel, float, Dict[str, Any]]:
    """
    Computes deterministic multi-factor severity level.
    Returns (SeverityLevel, severity_score_0_to_100, factors_dict).
    """
    norm_type = hazard_type.lower().replace(" ", "_")
    base_weight = HAZARD_CLASS_BASE_WEIGHTS.get(norm_type, 0.50)
    
    # 1. Size factor (0.0 to 0.30)
    # Area percentage: 0% to 15%+
    size_factor = min(0.30, (relative_area_pct / 12.0) * 0.30)
    
    # 2. Road Position factor (0.0 to 0.20)
    # Direct vehicle wheel track (center-left and center-right, bottom half of image)
    box_center_x = (bbox["x1"] + bbox["x2"]) / (2.0 * img_width)
    box_center_y = (bbox["y1"] + bbox["y2"]) / (2.0 * img_height)
    
    in_center_lane = 0.25 <= box_center_x <= 0.75
    in_lower_field = box_center_y >= 0.45
    
    position_factor = 0.0
    if in_center_lane and in_lower_field:
        position_factor = 0.20
    elif in_center_lane or in_lower_field:
        position_factor = 0.10
    else:
        position_factor = 0.04
    
    # 3. Water Presence modifier
    water_factor = 0.15 if (water_detected or norm_type == "waterlogging") else 0.0
    
    # 4. Confidence modifier (penalizes uncertain low-confidence detections)
    conf_factor = min(1.0, max(0.5, confidence))
    
    # Composite raw severity (0.0 to 1.0)
    raw_severity = (base_weight * 0.45 + size_factor + position_factor + water_factor) * conf_factor
    raw_severity = min(1.0, max(0.1, raw_severity))
    severity_score = round(raw_severity * 100, 1)
    
    # Categorization thresholds
    if severity_score >= 78.0:
        level = SeverityLevel.CRITICAL
    elif severity_score >= 58.0:
        level = SeverityLevel.HIGH
    elif severity_score >= 38.0:
        level = SeverityLevel.MEDIUM
    else:
        level = SeverityLevel.LOW
        
    factors = {
        "base_class_weight": round(base_weight, 2),
        "size_factor_contrib": round(size_factor, 2),
        "position_factor_contrib": round(position_factor, 2),
        "water_factor_contrib": round(water_factor, 2),
        "confidence_scalar": round(conf_factor, 2),
        "composite_severity_score": severity_score,
        "is_in_vehicle_wheel_path": in_center_lane and in_lower_field
    }
    
    return level, severity_score, factors
