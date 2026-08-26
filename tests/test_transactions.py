from httpx import AsyncClient


async def test_list_requires_auth(client: AsyncClient):
    resp = await client.get("/api/transactions")
    assert resp.status_code == 401


async def test_list_empty_dataset_shape(client: AsyncClient, auth_headers: dict):
    """No transactions seeded in the test DB — verifies pagination shape on an
    empty result rather than crashing."""
    resp = await client.get("/api/transactions", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"] == []
    assert body["pagination"]["total"] == 0
    assert body["pagination"]["has_next"] is False


async def test_invalid_status_rejected(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/transactions?status=NOTAREALSTATUS", headers=auth_headers)
    assert resp.status_code == 422


async def test_invalid_sort_by_rejected(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/transactions?sort_by=merchant", headers=auth_headers)
    assert resp.status_code == 422


async def test_amount_max_below_min_rejected(client: AsyncClient, auth_headers: dict):
    resp = await client.get(
        "/api/transactions?amount_min=1000&amount_max=10", headers=auth_headers
    )
    assert resp.status_code == 422


async def test_detail_404_for_missing_transaction(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/transactions/999999999", headers=auth_headers)
    assert resp.status_code == 404
