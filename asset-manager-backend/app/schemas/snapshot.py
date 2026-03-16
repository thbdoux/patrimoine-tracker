import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class SnapshotSchema(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    captured_at: datetime
    balance: Decimal
    balance_eur: Optional[Decimal]
    price_eur: Optional[Decimal]
    created_at: datetime

    class Config:
        from_attributes = True
