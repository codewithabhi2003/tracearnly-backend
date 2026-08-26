import asyncio

from httpx import AsyncClient

from tests.conftest import set_balance


async def test_rewards_catalogue(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/rewards", headers=auth_headers)
    assert resp.status_code == 200
    names = {r["name"] for r in resp.json()}
    assert "Swiggy ₹100 Voucher" in names


async def test_successful_redemption(client: AsyncClient, auth_headers: dict):
    token = auth_headers["Authorization"].split(" ")[1]
    await set_balance(client, token, 1000)

    balance_before = (await client.get("/api/rewards/balance", headers=auth_headers)).json()["balance"]
    resp = await client.post("/api/rewards/redeem", json={"reward_id": 2}, headers=auth_headers)  # Swiggy, 300
    assert resp.status_code == 200
    data = resp.json()
    assert data["coins_spent"] == 300
    assert data["new_balance"] == balance_before - 300


async def test_insufficient_balance(client: AsyncClient, auth_headers: dict):
    token = auth_headers["Authorization"].split(" ")[1]
    await set_balance(client, token, 100)  # less than any reward costs

    resp = await client.post("/api/rewards/redeem", json={"reward_id": 3}, headers=auth_headers)  # 600
    assert resp.status_code == 400
    assert "Insufficient" in resp.json()["detail"]


async def test_nonexistent_reward(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/rewards/redeem", json={"reward_id": 9999}, headers=auth_headers)
    assert resp.status_code == 404


async def test_balance_unchanged_after_failed_redemption(client: AsyncClient, auth_headers: dict):
    token = auth_headers["Authorization"].split(" ")[1]
    await set_balance(client, token, 50)
    before = (await client.get("/api/rewards/balance", headers=auth_headers)).json()["balance"]

    await client.post("/api/rewards/redeem", json={"reward_id": 1}, headers=auth_headers)  # 500, will fail

    after = (await client.get("/api/rewards/balance", headers=auth_headers)).json()["balance"]
    assert before == after == 50


async def test_concurrent_redemption_only_one_succeeds(client: AsyncClient, auth_headers: dict):
    """Two simultaneous redemptions against a balance that can only cover one —
    the SELECT FOR UPDATE row lock must serialize them so exactly one succeeds."""
    token = auth_headers["Authorization"].split(" ")[1]
    await set_balance(client, token, 300)  # exactly one Swiggy (300) redemption's worth

    results = await asyncio.gather(
        client.post("/api/rewards/redeem", json={"reward_id": 2}, headers=auth_headers),
        client.post("/api/rewards/redeem", json={"reward_id": 2}, headers=auth_headers),
    )
    statuses = sorted(r.status_code for r in results)
    assert statuses == [200, 400]

    final = (await client.get("/api/rewards/balance", headers=auth_headers)).json()["balance"]
    assert final == 0
