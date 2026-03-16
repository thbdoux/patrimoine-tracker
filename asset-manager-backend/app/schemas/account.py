import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class AccountSchema(BaseModel):
    id: uuid.UUID
    external_id: str
    source: str
    account_type: str
    label: Optional[str]
    currency: Optional[str]
    institution: Optional[str]
    iban: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
