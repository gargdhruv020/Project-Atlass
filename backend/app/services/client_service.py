"""
Client Service
Handles client queries and permission validation for reports.
"""

from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.models.client import Client
from app.models.report import Report

class ClientService:
    @staticmethod
    def get_client(db: Session, client_id: str) -> Optional[Client]:
        """Fetch a client by ID."""
        return db.query(Client).filter(Client.id == client_id).first()

    @staticmethod
    def check_report_access(db: Session, client_id: str, report_id: str) -> Tuple[bool, str]:
        """
        Verify if a client can access a given report.
        - If report is public -> access granted.
        - If client purchased the report -> access granted.
        - Otherwise -> access denied.
        """
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            return False, f"Report '{report_id}' does not exist."

        if report.access == "public":
            return True, f"Report '{report_id}' is publicly accessible."

        client = ClientService.get_client(db, client_id)
        if not client:
            return False, f"Client '{client_id}' not found."

        if client.has_access_to_report(report_id):
            return True, f"Client '{client.company}' has purchased report '{report_id}'."

        return False, f"Access denied: Client '{client.company}' has not purchased paid report '{report_id}'."
