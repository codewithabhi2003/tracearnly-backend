from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.redemption import RedemptionResponse
from app.schemas.reward import BalanceResponse, RedeemRequest, RedeemResponse, RewardResponse
from app.services.reward_service import list_redemptions, list_rewards, redeem_reward

router = APIRouter(prefix="/api/rewards", tags=["rewards"])


@router.get("", response_model=list[RewardResponse])
async def get_rewards(db: AsyncSession = Depends(get_db), _current_user: User = Depends(get_current_user)):
    rewards = await list_rewards(db)
    return rewards


@router.get("/balance", response_model=BalanceResponse)
async def get_balance(current_user: User = Depends(get_current_user)):
    return BalanceResponse(balance=current_user.coin_balance)


@router.post("/redeem", response_model=RedeemResponse)
async def redeem(
    payload: RedeemRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await redeem_reward(db, current_user.id, payload.reward_id)
    return RedeemResponse(**result)


@router.get("/redemptions", response_model=list[RedemptionResponse])
async def get_redemptions(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return await list_redemptions(db, current_user.id)
