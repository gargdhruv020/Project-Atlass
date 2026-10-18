"""
Market Research Reports Endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.report_service import ReportService
from app.schemas.report import ReportRead, ReportDetail
from app.schemas.market_metric import MarketMetricRead

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("", response_model=List[ReportRead])
def list_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List available market research reports."""
    return ReportService.list_reports(db, skip=skip, limit=limit)

@router.get("/{report_id}", response_model=ReportDetail)
def get_report(report_id: str, db: Session = Depends(get_db)):
    """Get report details along with all associated market metrics."""
    report = ReportService.get_report_by_id(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found.")
    return report

@router.get("/{report_id}/metrics", response_model=List[MarketMetricRead])
def get_report_metrics(
    report_id: str,
    metric: Optional[str] = None,
    region: Optional[str] = None,
    period: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Retrieve filtered metrics for a specific report."""
    return ReportService.search_metrics(
        db, report_id=report_id, metric_query=metric, region=region, period=period
    )
