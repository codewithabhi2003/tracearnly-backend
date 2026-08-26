"""
Test fixtures.

Uses a separate PostgreSQL database so tests never touch seeded demo data.

There's no login/signup in this app — every request acts on the single
implicit demo user (see app.dependencies.DEMO_USER_EMAIL), which
get_demo_user() creates lazily on first use if it doesn't exist yet.

Tests that care about balance call set_balance() to force it to a known
value before asserting.
"""

import os

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/tracearnly_test",
)
os.environ.setdefault("ENVIRONMENT", "test")

TEST_DATABASE_URL = os.environ["DATABASE_URL"]


from app.database import Base  # noqa: E402
from app.dependencies import DEMO_USER_EMAIL, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.reward import Reward  # noqa: E402


REWARDS = [
    {
        "id": 1,
        "name": "Amazon ₹100 Voucher",
        "description": "Redeemable on Amazon.in",
        "coin_cost": 500,
    },
    {
        "id": 2,
        "name": "Swiggy ₹100 Voucher",
        "description": "Redeemable on Swiggy",
        "coin_cost": 300,
    },
    {
        "id": 3,
        "name": "Movie Voucher ₹150",
        "description": "BookMyShow",
        "coin_cost": 600,
    },
]


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    """
    One-time schema setup using a short-lived engine.
    """

    setup_engine = create_async_engine(TEST_DATABASE_URL)

    async with setup_engine.begin() as conn:
        await conn.execute(
            text("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        )

        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(
        bind=setup_engine,
        expire_on_commit=False,
    )

    async with session_maker() as session:
        session.add_all(
            [Reward(**reward) for reward in REWARDS]
        )
        await session.commit()

    await setup_engine.dispose()

    yield


@pytest_asyncio.fixture
async def client():
    """
    Creates a fresh engine within each test's event loop and overrides
    get_db for the duration of the test.
    """

    engine = create_async_engine(TEST_DATABASE_URL)

    session_maker = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )

    async def _override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as ac:
        ac._session_maker = session_maker
        yield ac

    app.dependency_overrides.pop(get_db, None)

    await engine.dispose()


async def set_balance(
    client: AsyncClient,
    balance: int,
):
    """
    Directly sets the demo user's coin balance via the database,
    bypassing the API.

    Creates the demo user first if it doesn't exist yet.
    """

    from sqlalchemy import select

    from app.models.user import User

    async with client._session_maker() as session:
        user = await session.scalar(
            select(User).where(
                User.email == DEMO_USER_EMAIL
            )
        )

        if user is None:
            user = User(
                name="Demo User",
                email=DEMO_USER_EMAIL,
                password_hash="",
                coin_balance=balance,
            )
            session.add(user)
        else:
            user.coin_balance = balance

        await session.commit()