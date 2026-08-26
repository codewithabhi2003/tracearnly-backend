from httpx import AsyncClient


async def test_list_empty_dataset_shape(client: AsyncClient):
    """
    No transactions are seeded in the test DB.

    Verifies the pagination response shape on an empty result.
    """
    resp = await client.get("/api/transactions")

    assert resp.status_code == 200

    body = resp.json()

    assert body["data"] == []
    assert body["pagination"]["total"] == 0
    assert body["pagination"]["has_next"] is False


async def test_invalid_status_rejected(client: AsyncClient):
    resp = await client.get(
        "/api/transactions?status=NOTAREALSTATUS"
    )

    assert resp.status_code == 422


async def test_invalid_sort_by_rejected(client: AsyncClient):
    resp = await client.get(
        "/api/transactions?sort_by=merchant"
    )

    assert resp.status_code == 422


async def test_amount_max_below_min_rejected(client: AsyncClient):
    resp = await client.get(
        "/api/transactions?amount_min=1000&amount_max=10"
    )

    assert resp.status_code == 422


async def test_detail_404_for_missing_transaction(
    client: AsyncClient,
):
    resp = await client.get(
        "/api/transactions/999999999"
    )

    assert resp.status_code == 404