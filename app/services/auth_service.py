from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.models.user import User
from app.utils.security import hash_password, verify_password


class EmailAlreadyRegisteredError(Exception):
    """Raised specifically for the duplicate-email case — kept distinct from
    ValueError so a hashing failure or other bug can never be mistaken for
    this condition by the router's exception handling."""


async def register_user(db: AsyncSession, name: str, email: str, password: str) -> User:
    """
    Registers a new user. Per ASSUMPTIONS.md: since seeded transactions are shared
    demo data (not owned by any one user), a new user's starting coin balance is
    the sum of coins_earned across all SUCCESS transactions, so they can try the
    redeem flow immediately without waiting to "earn" anything themselves.
    """
    existing = await db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise EmailAlreadyRegisteredError("Email already registered")

    total_coins = await db.scalar(
        select(func.coalesce(func.sum(Transaction.coins_earned), 0)).where(
            Transaction.status == "SUCCESS"
        )
    )

    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        coin_balance=int(total_coins or 0),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    user = await db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user
