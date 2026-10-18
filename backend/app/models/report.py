"""
Report Model
Maps to existing 'reports' table in project_atlas MySQL database.
"""

from sqlalchemy import Column, String, Date, Enum
from sqlalchemy.orm import relationship
from app.db.session import Base

class Report(Base):
    __tablename__ = "reports"

    id = Column(String(10), primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    publisher = Column(String(100), nullable=False)
    published = Column(Date, nullable=False)
    sector = Column(String(50), nullable=False)
    access = Column(Enum("paid", "public", name="report_access_enum"), nullable=False)

    # Relationship to market metrics
    metrics = relationship("MarketMetric", back_populates="report", cascade="all, delete-orphan")
