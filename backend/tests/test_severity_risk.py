import pytest
from app.cv_service.severity_engine import calculate_severity
from app.cv_service.risk_engine import calculate_risk
from app.database.models import SeverityLevel

def test_severity_calculation_critical():
    # Open manhole in center lane
    bbox = {"x1": 250, "y1": 250, "x2": 390, "y2": 390}
    sev_level, sev_score, factors = calculate_severity(
        hazard_type="open_manhole",
        confidence=0.98,
        relative_area_pct=8.5,
        bbox=bbox,
        img_width=640,
        img_height=480,
        water_detected=False
    )
    assert sev_level == SeverityLevel.CRITICAL
    assert sev_score >= 78.0
    assert factors["is_in_vehicle_wheel_path"] is True

def test_severity_calculation_low():
    # Minor crack on shoulder
    bbox = {"x1": 10, "y1": 10, "x2": 50, "y2": 40}
    sev_level, sev_score, factors = calculate_severity(
        hazard_type="missing_sign",
        confidence=0.70,
        relative_area_pct=0.5,
        bbox=bbox,
        img_width=640,
        img_height=480
    )
    assert sev_level in [SeverityLevel.LOW, SeverityLevel.MEDIUM]
    assert sev_score < 45.0

def test_risk_score_deterministic_formula():
    sev_level = SeverityLevel.CRITICAL
    sev_score = 85.0
    factors = {"is_in_vehicle_wheel_path": True, "composite_severity_score": 85.0}
    
    risk_score, veh_risk, explain = calculate_risk(
        hazard_type="pothole",
        severity_level=sev_level,
        severity_score=sev_score,
        factors=factors,
        duplicate_count=3
    )
    
    assert 0 <= risk_score <= 100
    assert risk_score >= 75
    assert veh_risk in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]
    assert "pothole" in explain["primary_reason"].lower()
    assert len(explain["contributing_factors"]) == 4
