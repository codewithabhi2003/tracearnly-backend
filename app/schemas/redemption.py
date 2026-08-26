from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RedemptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reward_name: str
    coins_spent: int
    status: str
    created_at: datetime
