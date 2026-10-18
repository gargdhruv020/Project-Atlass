"""
Service and Permission Verification Tests
Tests read-only behavior against existing database records.
"""

from app.services.client_service import ClientService
from app.services.report_service import ReportService

def test_list_existing_reports(db):
    """Verify existing reports are retrievable from MySQL."""
    reports = ReportService.list_reports(db)
    assert len(reports) >= 3
    ids = [r.id for r in reports]
    assert "R-101" in ids
    assert "R-102" in ids
    assert "R-103" in ids

def test_client_permissions(db):
    """
    Verify client permissions:
    - C-01 has purchased R-101 and R-103.
    - C-02 has only purchased R-103.
    - R-102 is public, so any client or unauthenticated user can access.
    """
    # C-01 accessing R-101 (purchased paid report)
    has_access, msg = ClientService.check_report_access(db, "C-01", "R-101")
    assert has_access is True

    # C-02 accessing R-101 (unpurchased paid report)
    has_access, msg = ClientService.check_report_access(db, "C-02", "R-101")
    assert has_access is False
    assert "Access denied" in msg

    # C-02 accessing R-102 (public report)
    has_access, msg = ClientService.check_report_access(db, "C-02", "R-102")
    assert has_access is True
