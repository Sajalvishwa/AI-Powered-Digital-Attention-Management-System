import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

PATHS = [
    "daily",
    "focus-score",
    "distractions",
    "predictions",
    "insights",
    "summary",
    "trend",
]


def _url(name):
    for r in app.routes:
        if getattr(r, "path", "").endswith(f"/analytics/{name}"):
            return r.path
    pytest.fail(f"/analytics/{name} not registered in main.py")


@pytest.mark.parametrize("name", PATHS)
def test_requires_auth(name):
    assert client.get(_url(name)).status_code == 401