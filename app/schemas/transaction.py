from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TransactionQuery(BaseModel):
    # Pagination
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=25, ge=1, le=100)

    # Search
    search: str | None = Field(default=None, max_length=200)

    # Filters
    category: str | None = None
    status: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    amount_min: Decimal | None = Field(default=None, ge=0)
    amount_max: Decimal | None = Field(default=None, ge=0)

    # Sorting
    sort_by: str = Field(default="timestamp", pattern="^(timestamp|amount)$")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v.upper() not in {"SUCCESS", "FAILED", "PENDING"}:
            raise ValueError("status must be one of SUCCESS, FAILED, PENDING")
        return v.upper() if v else v

    @model_validator(mode="after")
    def validate_amount_range(self) -> "TransactionQuery":
        if self.amount_max is not None and self.amount_min is not None:
            if self.amount_max < self.amount_min:
                raise ValueError("amount_max must be >= amount_min")
        return self

    @model_validator(mode="after")
    def validate_date_range(self) -> "TransactionQuery":
        if self.date_from is not None and self.date_to is not None:
            if self.date_to < self.date_from:
                raise ValueError("date_to must be >= date_from")
        return self


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: str
    timestamp: datetime
    merchant: str
    category: str
    amount: Decimal
    currency: str
    status: str
    payment_method: str
    coins_earned: int


class PaginationMeta(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool


class TransactionListResponse(BaseModel):
    data: list[TransactionResponse]
    pagination: PaginationMeta
