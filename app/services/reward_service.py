from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.redemption import Redemption
from app.models.reward import Reward
from app.models.user import User


async def list_rewards(db: AsyncSession) -> list[Reward]:
    result = await db.execute(select(Reward).where(Reward.is_active == True).order_by(Reward.coin_cost))  # noqa: E712
    return list(result.scalars().all())


async def list_redemptions(db: AsyncSession, user_id: int) -> list[Redemption]:
    result = await db.execute(
        select(Redemption).where(Redemption.user_id == user_id).order_by(Redemption.created_at.desc())
    )
    return list(result.scalars().all())


async def redeem_reward(db: AsyncSession, user_id: int, reward_id: int) -> dict:
    """
    Atomic reward redemption. Uses SELECT FOR UPDATE on the user row to prevent
    a double-spend race condition where two concurrent requests both read the
    balance before either has deducted from it.
    """
    # Row-level lock — held until this transaction commits/rolls back.
    result = await db.execute(select(User).where(User.id == user_id).with_for_update())
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    reward = await db.get(Reward, reward_id)
    if reward is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reward not found")
    if not reward.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reward is no longer available")
    if user.coin_balance < reward.coin_cost:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient coins. Required: {reward.coin_cost}, Available: {user.coin_balance}",
        )

    user.coin_balance -= reward.coin_cost
    redemption = Redemption(
        user_id=user_id,
        reward_id=reward_id,
        reward_name=reward.name,
        coins_spent=reward.coin_cost,
        status="COMPLETED",
    )
    db.add(redemption)
    await db.flush()
    await db.commit()
    await db.refresh(redemption)

    return {
        "success": True,
        "reward_name": reward.name,
        "coins_spent": reward.coin_cost,
        "new_balance": user.coin_balance,
        "redeemed_at": redemption.created_at,
    }
