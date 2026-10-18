from pydantic import BaseModel, ConfigDict
from typing import Optional

class MarketMetricBase(BaseModel):
    report_id: Optional[str] = None
    metric: Optional[str] = None
    region: Optional[str] = None
    period: Optional[str] = None
    value: Optional[str] = None
    scope_note: Optional[str] = None

class MarketMetricRead(MarketMetricBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
