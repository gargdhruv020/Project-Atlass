from datetime import date
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from app.schemas.market_metric import MarketMetricRead

class ReportBase(BaseModel):
    id: str
    title: str
    publisher: str
    published: date
    sector: str
    access: str

class ReportRead(ReportBase):
    model_config = ConfigDict(from_attributes=True)

class ReportDetail(ReportRead):
    metrics: List[MarketMetricRead] = []
    model_config = ConfigDict(from_attributes=True)
