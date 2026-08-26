from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RewardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    coin_cost: int
    is_active: bool


class BalanceResponse(BaseModel):
    balance: int


class RedeemRequest(BaseModel):
    reward_id: int = Field(gt=0)


class RedeemResponse(BaseModel):
    success: bool
    reward_name: str
    coins_spent: int
    new_balance: int
    redeemed_at: datetime
