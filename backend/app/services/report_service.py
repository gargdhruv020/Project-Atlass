"""
Report Service
Queries reports and associated market metrics from MySQL.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.report import Report
from app.models.market_metric import MarketMetric

class ReportService:
    @staticmethod
    def list_reports(db: Session, skip: int = 0, limit: int = 100) -> List[Report]:
        """Retrieve list of available market research reports."""
        return db.query(Report).offset(skip).limit(limit).all()

    @staticmethod
    def get_report_by_id(db: Session, report_id: str) -> Optional[Report]:
        """Fetch report with its market metrics."""
        return db.query(Report).filter(Report.id == report_id).first()

    @staticmethod
    def search_metrics(
        db: Session,
        report_id: Optional[str] = None,
        metric_query: Optional[str] = None,
        region: Optional[str] = None,
        period: Optional[str] = None,
    ) -> List[MarketMetric]:
        """Query market metrics with flexible filters."""
        q = db.query(MarketMetric)
        if report_id:
            q = q.filter(MarketMetric.report_id == report_id)
        if metric_query:
            q = q.filter(MarketMetric.metric.ilike(f"%{metric_query}%"))
        if region:
            q = q.filter(MarketMetric.region.ilike(f"%{region}%"))
        if period:
            q = q.filter(MarketMetric.period.ilike(f"%{period}%"))
        return q.all()
