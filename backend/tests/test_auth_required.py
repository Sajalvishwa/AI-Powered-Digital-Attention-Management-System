"""Every private endpoint must refuse requests without a token."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

PRIVATE = [
    ("GET", "/api/v1/users/me"),
    ("GET", "/api/v1/users/me/settings"),
    ("GET", "/api/v1/goals"),
    ("GET", "/api/v1/activity/recent"),
    ("GET", "/api/v1/focus-sessions"),
    ("GET", "/api/v1/focus-sessions/active"),
    ("GET", "/api/v1/stats/today"),
    ("DELETE", "/api/v1/users/me/data?confirm=true"),
]


@pytest.mark.parametrize("method,path", PRIVATE)
def test_requires_token(method, path):
    assert client.request(method, path).status_code == 401


def test_garbage_token_rejected():
    r = client.get("/api/v1/users/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401
