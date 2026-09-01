from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.database.models import Hazard, HazardStatus, SeverityLevel, RoadConditionScore
from app.cv_service.road_condition import detect_geospatial_hotspots, calculate_road_condition_score
from app.cv_service.maintenance_prioritizer import get_ranked_maintenance_queue

class RoadInspectorToolbox:
    """
    Controlled backend tools for the AI Road Inspector Assistant.
    """
    @staticmethod
    def get_statistics(db: Session) -> Dict[str, Any]:
        total = db.query(Hazard).count()
        critical = db.query(Hazard).filter(Hazard.severity == SeverityLevel.CRITICAL).count()
        high = db.query(Hazard).filter(Hazard.severity == SeverityLevel.HIGH).count()
        unresolved = db.query(Hazard).filter(
            Hazard.status.in_([HazardStatus.DETECTED, HazardStatus.REVIEW_REQUIRED, HazardStatus.VERIFIED, HazardStatus.ASSIGNED, HazardStatus.IN_PROGRESS, HazardStatus.REOPENED])
        ).count()
        resolved = db.query(Hazard).filter(Hazard.status == HazardStatus.RESOLVED).count()
        
        # Most common hazard type
        types_count = {}
        for h in db.query(Hazard.type).all():
            t = h[0]
            types_count[t] = types_count.get(t, 0) + 1
        most_common = max(types_count.items(), key=lambda x: x[1])[0] if types_count else "pothole"
        
        return {
            "total_hazards": total,
            "critical_hazards": critical,
            "high_hazards": high,
            "unresolved_hazards": unresolved,
            "resolved_hazards": resolved,
            "resolution_rate_pct": round((resolved / max(1, total)) * 100, 1),
            "most_common_hazard_type": most_common,
            "active_hotspots_count": len(detect_geospatial_hotspots(db))
        }

    @staticmethod
    def get_hazards(
        db: Session, 
        severity: Optional[str] = None, 
        hazard_type: Optional[str] = None, 
        status: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        query = db.query(Hazard)
        if severity:
            query = query.filter(Hazard.severity == severity.upper())
        if hazard_type:
            query = query.filter(Hazard.type.ilike(f"%{hazard_type}%"))
        if status:
            query = query.filter(Hazard.status == status.upper())
            
        results = query.order_by(Hazard.risk_score.desc()).limit(limit).all()
        return [
            {
                "id": h.id,
                "type": h.type,
                "severity": h.severity.value,
                "risk_score": h.risk_score,
                "status": h.status.value,
                "road_segment": h.road_segment or h.address,
                "detected_at": h.detected_at.strftime("%Y-%m-%d %H:%M") if h.detected_at else "Recent"
            }
            for h in results
        ]

    @staticmethod
    def get_hotspots(db: Session) -> List[Dict[str, Any]]:
        return detect_geospatial_hotspots(db)

    @staticmethod
    def get_maintenance_priority(db: Session, limit: int = 5) -> List[Dict[str, Any]]:
        return get_ranked_maintenance_queue(db)[:limit]

    @staticmethod
    def get_road_condition(db: Session, road_name: Optional[str] = None) -> List[Dict[str, Any]]:
        query = db.query(RoadConditionScore)
        if road_name:
            query = query.filter(RoadConditionScore.road_name.ilike(f"%{road_name}%"))
        scores = query.all()
        return [
            {
                "road_name": s.road_name,
                "district": s.district,
                "score": s.score,
                "condition_label": s.condition_label,
                "hazard_density_per_km": s.hazard_density_per_km,
                "total_hazards": s.total_hazards,
                "critical_hazards": s.critical_hazards
            }
            for s in scores
        ]


class AIRoadAssistant:
    """
    AI Road Inspector Assistant with deterministic query grounding and tool dispatch.
    """
    def __init__(self):
        self.toolbox = RoadInspectorToolbox()

    def process_query(self, user_query: str, db: Session) -> Dict[str, Any]:
        q = user_query.lower().strip()
        
        tool_called = None
        tool_result = None
        response_text = ""
        suggested_actions = []

        if "critical" in q or "dangerous" in q or "urgent" in q:
            tool_called = "get_hazards(severity='CRITICAL')"
            tool_result = self.toolbox.get_hazards(db, severity="CRITICAL", limit=5)
            count = len(tool_result)
            response_text = (
                f"I found **{count} critical road hazards** currently requiring urgent attention in the system.\n\n"
                f"The highest-risk hazard is **{tool_result[0]['type'].replace('_', ' ').title()}** on `{tool_result[0]['road_segment']}` "
                f"with a vehicle risk score of **{tool_result[0]['risk_score']}/100**."
                if count > 0 else "There are currently zero critical hazards in the active queue."
            )
            suggested_actions = ["Assign Field Inspector", "View on Live Map", "Export Priority List"]

        elif "priority" in q or "attention first" in q or "maintenance" in q or "repair first" in q:
            tool_called = "get_maintenance_priority()"
            tool_result = self.toolbox.get_maintenance_priority(db, limit=5)
            if tool_result:
                top = tool_result[0]
                response_text = (
                    f"Based on RoadGuard's deterministic priority ranking engine, the hazard requiring attention first is:\n\n"
                    f"**Rank #1: {top['type'].replace('_', ' ').title()} (ID: {top['hazard_id']})**\n"
                    f"- **Location**: {top['address']}\n"
                    f"- **Severity**: {top['severity']}\n"
                    f"- **Priority Score**: {top['priority_score']}/100\n"
                    f"- **Citizen Reports**: {top['duplicate_count']} reports\n\n"
                    f"Immediate municipal asphalt crew dispatch is recommended."
                )
            else:
                response_text = "The maintenance queue is currently clear."
            suggested_actions = ["Schedule Repair Task", "View Hotspots", "Filter by District"]

        elif "hotspot" in q or "area" in q or "worst" in q or "corridor" in q:
            tool_called = "get_hotspots()"
            tool_result = self.toolbox.get_hotspots(db)
            if tool_result:
                worst = tool_result[0]
                response_text = (
                    f"RoadGuard AI identified **{len(tool_result)} active hazard hotspots** across the city.\n\n"
                    f"**Worst Affected Area**: `{worst['area_name']}`\n"
                    f"- **Total Hazards**: {worst['total_hazards']} ({worst['critical_count']} Critical, {worst['high_count']} High)\n"
                    f"- **Hotspot Risk Index**: {worst['hotspot_risk_score']}/100\n"
                    f"- **AI Recommendation**: {worst['ai_recommendation']}"
                )
            else:
                response_text = "No severe hazard hotspots currently detected."
            suggested_actions = ["Highlight on Map", "Generate Area Report", "Dispatch Field Inspector"]

        elif "how many" in q or "unresolved" in q or "stat" in q or "summary" in q or "overview" in q:
            tool_called = "get_statistics()"
            stats = self.toolbox.get_statistics(db)
            tool_result = stats
            response_text = (
                f"### RoadGuard AI System Overview\n"
                f"- **Total Hazards Recorded**: {stats['total_hazards']}\n"
                f"- **Unresolved In-Queue**: **{stats['unresolved_hazards']}** ({stats['critical_hazards']} Critical)\n"
                f"- **Successfully Repaired**: {stats['resolved_hazards']} ({stats['resolution_rate_pct']}% resolution rate)\n"
                f"- **Most Frequent Hazard**: `{stats['most_common_hazard_type'].replace('_', ' ').title()}`\n"
                f"- **Active Geographic Hotspots**: {stats['active_hotspots_count']}"
            )
            suggested_actions = ["View Admin Dashboard", "Generate Weekly Report", "Open Maintenance Queue"]

        elif "pothole" in q:
            tool_called = "get_hazards(hazard_type='pothole')"
            tool_result = self.toolbox.get_hazards(db, hazard_type="pothole", limit=5)
            response_text = (
                f"Retrieved **{len(tool_result)} high-risk potholes** from the database. "
                f"Potholes represent the primary category of vehicle rim damage reports this month."
            )
            suggested_actions = ["View Pothole Map", "Assign Patch Crew", "Review Citizen Reports"]

        else:
            # General fallback query using statistics tool
            tool_called = "get_statistics()"
            stats = self.toolbox.get_statistics(db)
            tool_result = stats
            response_text = (
                f"I am the **RoadGuard AI Inspector Assistant**. I can query real-time road conditions, "
                f"hazard severity metrics, maintenance priorities, and geospatial hotspots.\n\n"
                f"Currently tracking **{stats['unresolved_hazards']} unresolved hazards** across city corridors. "
                f"Ask me about critical hazards, road scores, or maintenance recommendations!"
            )
            suggested_actions = ["Show critical hazards", "Which road needs attention first?", "Summarize hotspots"]

        return {
            "query": user_query,
            "tool_called": tool_called,
            "tool_result": tool_result,
            "response": response_text,
            "suggested_actions": suggested_actions,
            "timestamp": datetime.utcnow().isoformat()
        }

assistant_instance = AIRoadAssistant()
