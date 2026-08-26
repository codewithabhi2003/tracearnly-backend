import uuid

from httpx import AsyncClient


async def test_register_and_login(client: AsyncClient):
    email = f"reg-{uuid.uuid4().hex[:8]}@example.com"
    resp = await client.post(
        "/api/auth/register",
        json={"name": "Alice", "email": email, "password": "password123"},
    )
    assert resp.status_code == 201
    assert "access_token" in resp.json()

    resp = await client.post("/api/auth/login", json={"email": email, "password": "password123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_duplicate_email_rejected(client: AsyncClient):
    email = f"dup-{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        "/api/auth/register", json={"name": "Bob", "email": email, "password": "password123"}
    )
    resp = await client.post(
        "/api/auth/register", json={"name": "Bob2", "email": email, "password": "password123"}
    )
    assert resp.status_code == 409


async def test_wrong_password_rejected(client: AsyncClient):
    email = f"wp-{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        "/api/auth/register", json={"name": "Carol", "email": email, "password": "password123"}
    )
    resp = await client.post("/api/auth/login", json={"email": email, "password": "wrongpassword"})
    assert resp.status_code == 401


async def test_me_requires_auth(client: AsyncClient):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


async def test_me_returns_current_user(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert "email" in resp.json()
