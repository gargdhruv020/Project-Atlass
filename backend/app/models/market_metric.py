"""
Market Metric Model
Maps to existing 'market_metrics' table in project_atlas MySQL database.
"""

from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base

class MarketMetric(Base):
    __tablename__ = "market_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    report_id = Column(String(10), ForeignKey("reports.id"), nullable=True, index=True)
    metric = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    period = Column(String(50), nullable=True)
    value = Column(String(50), nullable=True)
    scope_note = Column(Text, nullable=True)

    # Relationship to report
    report = relationship("Report", back_populates="metrics")
