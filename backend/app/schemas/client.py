from pydantic import BaseModel, ConfigDict
from typing import Optional

class ClientBase(BaseModel):
    id: str
    company: str
    contact_email: str
    purchased_reports: str

class ClientRead(ClientBase):
    model_config = ConfigDict(from_attributes=True)

class ClientAccessCheck(BaseModel):
    client_id: str
    report_id: str
    has_access: bool
    company: Optional[str] = None
    reason: Optional[str] = None
