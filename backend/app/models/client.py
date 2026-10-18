"""
Client Model
Maps to existing 'clients' table in project_atlas MySQL database.
"""

from sqlalchemy import Column, String, Text
from app.db.session import Base

class Client(Base):
    __tablename__ = "clients"

    id = Column(String(10), primary_key=True, index=True)
    company = Column(String(100), nullable=False)
    contact_email = Column(String(100), nullable=False)
    purchased_reports = Column(Text, nullable=False)

    def has_access_to_report(self, report_id: str) -> bool:
        """Check if client has purchased or has access to report_id."""
        if not self.purchased_reports:
            return False
        purchased_list = [r.strip() for r in self.purchased_reports.split(",")]
        return report_id in purchased_list
