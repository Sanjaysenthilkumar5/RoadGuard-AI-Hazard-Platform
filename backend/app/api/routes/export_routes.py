import csv
import io
import json
from fastapi import APIRouter, Depends, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.database.models import Hazard
from app.ai_service.report_generator import generate_executive_report

router = APIRouter(prefix="/export", tags=["Export"])

@router.get("/csv")
def export_hazards_csv(db: Session = Depends(get_db)):
    hazards = db.query(Hazard).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers
    writer.writerow([
        "Hazard ID", "Type", "Severity", "Risk Score", "Vehicle Risk",
        "Latitude", "Longitude", "Address", "Road Segment", "Status",
        "Duplicate Reports", "Detected At", "Model Version"
    ])
    
    for h in hazards:
        writer.writerow([
            h.id,
            h.type,
            h.severity.value,
            h.risk_score,
            h.vehicle_risk.value,
            h.latitude,
            h.longitude,
            h.address or "",
            h.road_segment or "",
            h.status.value,
            h.duplicate_count or 1,
            h.detected_at.strftime("%Y-%m-%d %H:%M:%S") if h.detected_at else "",
            h.model_version or ""
        ])
        
    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=roadguard_hazards_export.csv"}
    )

@router.get("/json")
def export_hazards_json(db: Session = Depends(get_db)):
    hazards = db.query(Hazard).all()
    data = [
        {
            "id": h.id,
            "type": h.type,
            "severity": h.severity.value,
            "risk_score": h.risk_score,
            "vehicle_risk": h.vehicle_risk.value,
            "latitude": h.latitude,
            "longitude": h.longitude,
            "address": h.address,
            "road_segment": h.road_segment,
            "status": h.status.value,
            "duplicate_count": h.duplicate_count,
            "detected_at": h.detected_at.isoformat() if h.detected_at else None
        }
        for h in hazards
    ]
    return Response(
        content=json.dumps(data, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=roadguard_hazards.json"}
    )

@router.get("/print-report", response_class=HTMLResponse)
def get_printable_html_report(db: Session = Depends(get_db)):
    report = generate_executive_report(db)
    
    breakdown_rows = "".join([
        f"<tr><td>{item['type']}</td><td><strong>{item['count']}</strong></td><td>{item['pct']}%</td></tr>"
        for item in report["hazard_type_breakdown"]
    ])
    
    hotspot_rows = "".join([
        f"<tr><td>{h['area_name']}</td><td>{h['total_hazards']}</td><td>{h['critical_count']}</td><td><span class='badge critical'>Risk {h['hotspot_risk_score']}/100</span></td></tr>"
        for h in report["active_hotspots"]
    ])

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{report['title']}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; color: #1e293b; line-height: 1.6; }}
        .header {{ border-bottom: 2px solid #0284c7; padding-bottom: 15px; margin-bottom: 30px; }}
        .title {{ font-size: 26px; font-weight: 700; color: #0f172a; margin: 0; }}
        .meta {{ color: #64748b; font-size: 14px; margin-top: 5px; }}
        .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 30px; }}
        .card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; text-align: center; }}
        .card .val {{ font-size: 24px; font-weight: 700; color: #0284c7; }}
        .card .lbl {{ font-size: 12px; text-transform: uppercase; color: #64748b; margin-top: 4px; }}
        .section {{ margin-bottom: 30px; }}
        .section h3 {{ font-size: 18px; color: #0f172a; border-left: 4px solid #0284c7; padding-left: 10px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; }}
        th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
        th {{ background: #f1f5f9; color: #475569; font-weight: 600; }}
        .summary-box {{ background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 8px; padding: 16px; color: #0369a1; }}
        .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }}
        .badge.critical {{ background: #ffe4e6; color: #e11d48; }}
        @media print {{ body {{ margin: 0; }} }}
    </style>
</head>
<body>
    <div class="header">
        <h1 class="title">🛡️ ROADGUARD AI — EXECUTIVE ROAD INTELLIGENCE REPORT</h1>
        <div class="meta">Report ID: {report['report_id']} | Generated: {report['generated_at']} | Scope: {report['period']}</div>
    </div>

    <div class="grid">
        <div class="card">
            <div class="val">{report['metrics']['total_hazards']}</div>
            <div class="lbl">Total Anomalies</div>
        </div>
        <div class="card">
            <div class="val" style="color: #e11d48;">{report['metrics']['critical_hazards']}</div>
            <div class="lbl">Critical Safety Risks</div>
        </div>
        <div class="card">
            <div class="val" style="color: #10b981;">{report['metrics']['resolved_hazards']}</div>
            <div class="lbl">Repaired & Resolved</div>
        </div>
        <div class="card">
            <div class="val">{report['metrics']['resolution_rate_pct']}%</div>
            <div class="lbl">Resolution Velocity</div>
        </div>
    </div>

    <div class="section">
        <h3>AI Executive Synthesis</h3>
        <div class="summary-box">
            {report['ai_executive_summary']}
        </div>
    </div>

    <div class="section">
        <h3>Top Defect Breakdown</h3>
        <table>
            <thead><tr><th>Hazard Classification</th><th>Volume</th><th>Percentage</th></tr></thead>
            <tbody>{breakdown_rows}</tbody>
        </table>
    </div>

    <div class="section">
        <h3>Priority Geographic Hotspots</h3>
        <table>
            <thead><tr><th>Corridor / Zone</th><th>Hazards Count</th><th>Critical Hazards</th><th>Hotspot Risk Index</th></tr></thead>
            <tbody>{hotspot_rows}</tbody>
        </table>
    </div>

    <div class="section">
        <h3>Operational Recommendations</h3>
        <ul>
            {"".join([f"<li>{r}</li>" for r in report['recommendations']])}
        </ul>
    </div>
</body>
</html>"""
    return HTMLResponse(content=html_content)
