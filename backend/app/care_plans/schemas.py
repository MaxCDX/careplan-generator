from datetime import datetime

from pydantic import BaseModel


class CarePlanRead(BaseModel):
    """Response body for generated care plan content."""

    id: str
    order_id: str
    model: str
    care_plan: str
    created_at: datetime | None = None
