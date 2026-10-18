"""
Database Query Tool
Provides structured SQL retrieval over MySQL tables (reports, market_metrics, clients).
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
class DatabaseTool:
    @staticmethod
    def query_metrics(
        db: Session,
        report_id: Optional[str] = None,
        metric: Optional[str] = None,
        region: Optional[str] = None,
        period: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query structured market metrics."""
        from app.services.report_service import ReportService
        results = ReportService.search_metrics(
            db=db,
            report_id=report_id,
            metric_query=metric,
            region=region,
            period=period
        )
        return [
            {
                "id": m.id,
                "report_id": m.report_id,
                "metric": m.metric,
                "region": m.region,
                "period": m.period,
                "value": m.value,
                "scope_note": m.scope_note,
                "source_type": "relational_sql"
            }
            for m in results
        ]

    @staticmethod
    def check_client_access(db: Session, client_id: str, report_id: str) -> Dict[str, Any]:
        """Validate client access for a given report."""
        from app.services.client_service import ClientService
        has_access, reason = ClientService.check_report_access(db, client_id, report_id)
        return {
            "client_id": client_id,
            "report_id": report_id,
            "has_access": has_access,
            "reason": reason
        }
