import asyncio

from httpx import AsyncClient

from tests.conftest import set_balance


async def test_rewards_catalogue(client: AsyncClient):
    resp = await client.get("/api/rewards")

    assert resp.status_code == 200

    names = {reward["name"] for reward in resp.json()}

    assert "Swiggy ₹100 Voucher" in names


async def test_successful_redemption(client: AsyncClient):
    await set_balance(client, 1000)

    balance_before = (
        await client.get("/api/rewards/balance")
    ).json()["balance"]

    resp = await client.post(
        "/api/rewards/redeem",
        json={"reward_id": 2},
    )

    assert resp.status_code == 200

    data = resp.json()

    assert data["coins_spent"] == 300
    assert data["new_balance"] == balance_before - 300


async def test_insufficient_balance(client: AsyncClient):
    await set_balance(client, 100)

    resp = await client.post(
        "/api/rewards/redeem",
        json={"reward_id": 3},
    )

    assert resp.status_code == 400
    assert "Insufficient" in resp.json()["detail"]


async def test_nonexistent_reward(client: AsyncClient):
    resp = await client.post(
        "/api/rewards/redeem",
        json={"reward_id": 9999},
    )

    assert resp.status_code == 404


async def test_balance_unchanged_after_failed_redemption(
    client: AsyncClient,
):
    await set_balance(client, 50)

    before = (
        await client.get("/api/rewards/balance")
    ).json()["balance"]

    await client.post(
        "/api/rewards/redeem",
        json={"reward_id": 1},
    )

    after = (
        await client.get("/api/rewards/balance")
    ).json()["balance"]

    assert before == after == 50


async def test_concurrent_redemption_only_one_succeeds(
    client: AsyncClient,
):
    """
    Two simultaneous redemptions against a balance that can only cover
    one redemption.

    The SELECT FOR UPDATE row lock must serialize them so exactly one
    succeeds.
    """
    await set_balance(client, 300)

    results = await asyncio.gather(
        client.post(
            "/api/rewards/redeem",
            json={"reward_id": 2},
        ),
        client.post(
            "/api/rewards/redeem",
            json={"reward_id": 2},
        ),
    )

    statuses = sorted(
        response.status_code
        for response in results
    )

    assert statuses == [200, 400]

    final = (
        await client.get("/api/rewards/balance")
    ).json()["balance"]

    assert final == 0