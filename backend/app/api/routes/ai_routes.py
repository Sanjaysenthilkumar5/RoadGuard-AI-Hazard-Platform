from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.ai_service.assistant import assistant_instance
from app.ai_service.report_generator import generate_executive_report

router = APIRouter(prefix="/ai", tags=["AI Road Assistant & Reports"])

class AIChatRequest(BaseModel):
    query: str

@router.post("/chat")
def chat_with_road_assistant(req: AIChatRequest, db: Session = Depends(get_db)):
    """
    Queries the AI Road Inspector Assistant.
    Executes controlled backend database tools and returns grounded answers.
    """
    result = assistant_instance.process_query(req.query, db)
    return result

@router.post("/reports/generate")
def generate_report(
    days_back: int = Query(7, ge=1, le=90),
    period_name: str = Query("Weekly Report (Last 7 Days)"),
    db: Session = Depends(get_db)
):
    """
    Generates a structured, factually grounded Smart City Road Condition Report.
    """
    report = generate_executive_report(db, period_label=period_name, days_back=days_back)
    return report
