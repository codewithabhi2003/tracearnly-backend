from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.analytics import CategoryBreakdown, MonthlyBreakdown, SummaryResponse
from app.services.analytics_service import get_category_breakdown, get_monthly_trend, get_summary

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/categories", response_model=list[CategoryBreakdown])
async def categories(db: AsyncSession = Depends(get_db), _current_user: User = Depends(get_current_user)):
    rows = await get_category_breakdown(db)
    return [CategoryBreakdown(category=r.category, total=r.total, count=r.count) for r in rows]


@router.get("/monthly", response_model=list[MonthlyBreakdown])
async def monthly(db: AsyncSession = Depends(get_db), _current_user: User = Depends(get_current_user)):
    rows = await get_monthly_trend(db)
    return [MonthlyBreakdown(month=r.month, total=r.total, count=r.count) for r in rows]


@router.get("/summary", response_model=SummaryResponse)
async def summary(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    data = await get_summary(db, current_user.coin_balance)
    return SummaryResponse(**data)
