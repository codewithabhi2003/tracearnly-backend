from fastapi import Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.transaction import Transaction
from app.models.user import User


# There's no login/signup in this app — every request acts on a single
# implicit demo user, identified by this fixed email.
# The seed script creates this row with a starting balance equal to the
# sum of all coins earned across seeded SUCCESS transactions.
#
# get_demo_user() also creates it on first use as a fallback, so the app
# still works even if someone runs it against a database that wasn't seeded.

DEMO_USER_EMAIL = "demo@tracearnly.local"


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def get_demo_user(
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await db.scalar(
        select(User).where(User.email == DEMO_USER_EMAIL)
    )

    if user is not None:
        return user

    # Fallback for a database that was created but never seeded.
    total_coins = await db.scalar(
        select(
            func.coalesce(
                func.sum(Transaction.coins_earned),
                0,
            )
        ).where(
            Transaction.status == "SUCCESS"
        )
    )

    user = User(
        name="Demo User",
        email=DEMO_USER_EMAIL,
        password_hash="",
        coin_balance=int(total_coins or 0),
    )

    db.add(user)

    try:
        await db.commit()
    except Exception:
        # Another concurrent request may have just created it.
        # Re-fetch rather than returning an error.
        await db.rollback()

        user = await db.scalar(
            select(User).where(User.email == DEMO_USER_EMAIL)
        )

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create or find demo user",
            )

        return user

    await db.refresh(user)
    return user