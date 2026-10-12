import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.core import rate_limit
from app.core.database import get_db
from app.main import app
from app.services import auth_service, ingestion_service


TEST_USER_ID = uuid.UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def client(monkeypatch):
    rate_limit.reset()

    def override_db():
        yield None

    def override_user():
        return SimpleNamespace(id=TEST_USER_ID)

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user

    monkeypatch.setattr(
        auth_service,
        "register",
        lambda db, body: {
            "id": TEST_USER_ID,
            "name": body.name,
            "email": body.email,
        },
    )
    monkeypatch.setattr(
        auth_service,
        "login",
        lambda db, email, password: {
            "access_token": "test-access",
            "refresh_token": "test-refresh",
            "token_type": "bearer",
        },
    )
    monkeypatch.setattr(
        auth_service,
        "refresh",
        lambda db, token: {
            "access_token": "test-access",
            "refresh_token": "test-refresh",
            "token_type": "bearer",
        },
    )
    monkeypatch.setattr(
        ingestion_service,
        "ingest",
        lambda db, user, body: {
            "received": len(body.sessions),
            "inserted": len(body.sessions),
            "duplicates": 0,
            "skipped": 0,
        },
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    rate_limit.reset()


def register_payload(email="rate-test@example.com"):
    return {
        "name": "Rate Test",
        "email": email,
        "password": "StrongPass123",
    }


def login_payload(email="rate-test@example.com"):
    return {"email": email, "password": "StrongPass123"}


def activity_payload():
    return {
        "sessions": [
            {
                "client_id": "b8f25c6e-39c0-4b71-91ef-aecf55e0c123",
                "app_name": "Test App",
                "window_title": "Rate Limit Test",
                "is_idle": False,
                "started_at": "2026-10-11T10:00:00Z",
                "ended_at": "2026-10-11T10:01:00Z",
                "focus_session_id": None,
            }
        ]
    }


def assert_rate_limited(response):
    assert response.status_code == 429
    assert "Too many requests" in response.json()["detail"]
    assert int(response.headers["Retry-After"]) >= 1


def test_register_endpoint_limit(client):
    for i in range(3):
        response = client.post(
            "/api/v1/auth/register",
            json=register_payload(f"register{i}@example.com"),
        )
        assert response.status_code == 201

    response = client.post(
        "/api/v1/auth/register",
        json=register_payload("register-extra@example.com"),
    )
    assert_rate_limited(response)


def test_login_endpoint_email_limit(client):
    for _ in range(5):
        response = client.post(
            "/api/v1/auth/login",
            json=login_payload("same@example.com"),
        )
        assert response.status_code == 200

    response = client.post(
        "/api/v1/auth/login",
        json=login_payload("same@example.com"),
    )
    assert_rate_limited(response)


def test_login_endpoint_ip_limit(client):
    for i in range(20):
        response = client.post(
            "/api/v1/auth/login",
            json=login_payload(f"person{i}@example.com"),
        )
        assert response.status_code == 200

    response = client.post(
        "/api/v1/auth/login",
        json=login_payload("person20@example.com"),
    )
    assert_rate_limited(response)


def test_refresh_endpoint_limit(client):
    payload = {"refresh_token": "mock-refresh-token"}

    for _ in range(30):
        response = client.post("/api/v1/auth/refresh", json=payload)
        assert response.status_code == 200

    response = client.post("/api/v1/auth/refresh", json=payload)
    assert_rate_limited(response)


def test_activity_batch_endpoint_limit(client):
    payload = activity_payload()

    for _ in range(30):
        response = client.post("/api/v1/activity/batch", json=payload)
        assert response.status_code == 200

    response = client.post("/api/v1/activity/batch", json=payload)
    assert_rate_limited(response)
