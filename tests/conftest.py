"""
Test fixtures. Uses a *separate* Postgres database (TEST_DATABASE_URL, defaults
to the same server as DATABASE_URL with a `_test` suffix) so tests never touch
seeded demo data. Tables are created fresh once per test session; each test
gets its own uniquely-emailed user to avoid cross-test interference without
needing full transaction-rollback isolation.
"""

import os
import uuid

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/tracearnly_test",
)
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-pytest-only-32ch")
os.environ.setdefault("ENVIRONMENT", "test")

TEST_DATABASE_URL = os.environ["DATABASE_URL"]

from app.database import Base  # noqa: E402
from app.dependencies import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.reward import Reward  # noqa: E402

REWARDS = [
    {"id": 1, "name": "Amazon ₹100 Voucher", "description": "Redeemable on Amazon.in", "coin_cost": 500},
    {"id": 2, "name": "Swiggy ₹100 Voucher", "description": "Redeemable on Swiggy", "coin_cost": 300},
    {"id": 3, "name": "Movie Voucher ₹150", "description": "BookMyShow", "coin_cost": 600},
]


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    """One-time schema setup, using its own short-lived engine so it doesn't
    leak a connection into any particular test's event loop."""
    setup_engine = create_async_engine(TEST_DATABASE_URL)
    async with setup_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(bind=setup_engine, expire_on_commit=False)
    async with session_maker() as session:
        session.add_all([Reward(**r) for r in REWARDS])
        await session.commit()
    await setup_engine.dispose()
    yield


@pytest_asyncio.fixture
async def client():
    """
    Creates a fresh engine *within this test's own event loop* (pytest-asyncio
    gives each test function its own loop by default) and overrides get_db for
    the duration of the test. A shared session-wide engine here previously
    caused SELECT ... FOR UPDATE to not properly block a concurrent request in
    test_concurrent_redemption_only_one_succeeds, even though the same
    scenario against the real running server serializes correctly — engine
    lifetime matching event-loop lifetime avoids that class of problem.
    """
    engine = create_async_engine(TEST_DATABASE_URL)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async def _override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac._session_maker = session_maker  # stashed for the set_balance helper
        yield ac
    app.dependency_overrides.pop(get_db, None)
    await engine.dispose()


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient):
    """Registers a fresh user (unique email) and returns their auth header."""
    email = f"user-{uuid.uuid4().hex[:12]}@example.com"
    resp = await client.post(
        "/api/auth/register",
        json={"name": "Test User", "email": email, "password": "password123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def set_balance(client: AsyncClient, token: str, balance: int):
    """Directly sets a user's coin balance via the DB, bypassing the API."""
    from app.models.user import User
    from app.utils.security import decode_token

    payload = decode_token(token)
    user_id = int(payload["sub"])
    async with client._session_maker() as session:
        user = await session.get(User, user_id)
        user.coin_balance = balance
        await session.commit()
