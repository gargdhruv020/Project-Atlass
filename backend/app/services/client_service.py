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

    @staticmethod
    def get_permitted_reports(db: Session, client_id: str) -> set:
        """
        Retrieves complete set of permitted report IDs for a client from MySQL:
        Combines explicit purchased reports with all public reports.
        """
        client = ClientService.get_client(db, client_id)
        if not client:
            return set()

        purchased = {r.strip() for r in (client.purchased_reports or "").split(",") if r.strip()}
        public_reports = {r.id for r in db.query(Report).filter(Report.access == "public").all()}
        return purchased.union(public_reports)

    @staticmethod
    def get_unpurchased_reports_metadata(db: Session, client_id: str) -> list:
        """
        Retrieves safe catalog metadata (id, title, access) for reports the client
        has NOT purchased, without revealing protected document contents or figures.
        """
        permitted = ClientService.get_permitted_reports(db, client_id)
        all_reports = db.query(Report).all()
        return [
            {
                "id": r.id,
                "title": r.title,
                "access": r.access
            }
            for r in all_reports
            if r.id not in permitted
        ]
