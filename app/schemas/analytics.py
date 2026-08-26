from decimal import Decimal

from pydantic import BaseModel


class CategoryBreakdown(BaseModel):
    category: str
    total: Decimal
    count: int


class MonthlyBreakdown(BaseModel):
    month: str  # "YYYY-MM"
    total: Decimal
    count: int


class SummaryResponse(BaseModel):
    total_spending: Decimal
    transaction_count: int
    successful_count: int
    failed_count: int
    pending_count: int
    coin_balance: int
    total_coins_earned: int
    top_category: str | None
    top_merchant: str | None
