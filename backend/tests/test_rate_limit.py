
import pytest
from fastapi import HTTPException

from app.core import rate_limit


@pytest.fixture(autouse=True)
def clear_rate_limits():
    rate_limit.reset()
    yield
    rate_limit.reset()


def test_register_limit_three_per_minute():
    for i in range(3):
        rate_limit.check("register:127.0.0.1", 3, 60, now=100.0 + i)

    with pytest.raises(HTTPException) as exc:
        rate_limit.check("register:127.0.0.1", 3, 60, now=104.0)

    assert exc.value.status_code == 429
    assert "Retry-After" in exc.value.headers


def test_login_ip_limit_twenty_per_minute():
    for i in range(20):
        rate_limit.check("login:ip:127.0.0.1", 20, 60, now=100.0 + i)

    with pytest.raises(HTTPException) as exc:
        rate_limit.check("login:ip:127.0.0.1", 20, 60, now=121.0)

    assert exc.value.status_code == 429
    assert "Retry-After" in exc.value.headers


def test_login_email_limit_five_per_minute():
    for i in range(5):
        rate_limit.check("login:email:test@example.com", 5, 60, now=100.0 + i)

    with pytest.raises(HTTPException) as exc:
        rate_limit.check(
            "login:email:test@example.com", 5, 60, now=106.0
        )

    assert exc.value.status_code == 429
    assert "Retry-After" in exc.value.headers


def test_refresh_limit_thirty_per_minute():
    for i in range(30):
        rate_limit.check("refresh:127.0.0.1", 30, 60, now=100.0 + i)

    with pytest.raises(HTTPException) as exc:
        rate_limit.check("refresh:127.0.0.1", 30, 60, now=131.0)

    assert exc.value.status_code == 429
    assert "Retry-After" in exc.value.headers


def test_activity_batch_limit_thirty_per_user():
    for i in range(30):
        rate_limit.check("batch:user-123", 30, 60, now=100.0 + i)

    with pytest.raises(HTTPException) as exc:
        rate_limit.check("batch:user-123", 30, 60, now=131.0)

    assert exc.value.status_code == 429
    assert "Retry-After" in exc.value.headers


def test_window_expires():
    for _ in range(3):
        rate_limit.check("window-test", 3, 60, now=1000.0)

    rate_limit.check("window-test", 3, 60, now=1061.0)


def test_keys_are_independent():
    for _ in range(3):
        rate_limit.check("register:ip-a", 3, 60, now=500.0)

    rate_limit.check("register:ip-b", 3, 60, now=500.0)


def test_reset_clears_counters():
    for _ in range(3):
        rate_limit.check("reset-test", 3, 60, now=10.0)

    rate_limit.reset()
    rate_limit.check("reset-test", 3, 60, now=10.0)
