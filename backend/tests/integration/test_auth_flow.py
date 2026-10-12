"""Login, refresh-token rotation, logout, bad tokens, brute-force protection."""
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings

API = "/api/v1"


def test_duplicate_email_is_rejected_case_insensitively(client):
    body = {"name": "X", "email": "dup@example.com", "password": "Strong123"}
    assert client.post(f"{API}/auth/register", json=body).status_code == 201
    again = {**body, "email": "DUP@Example.com"}
    assert client.post(f"{API}/auth/register", json=again).status_code == 409


def test_weak_password_is_rejected(client):
    body = {"name": "X", "email": "weak@example.com", "password": "alllowercase1"}
    assert client.post(f"{API}/auth/register", json=body).status_code == 422


def test_login_errors_do_not_reveal_which_part_was_wrong(client, signup):
    signup("real@example.com")
    wrong_pw = client.post(f"{API}/auth/login", json={"email": "real@example.com", "password": "Wrong123"})
    no_user = client.post(f"{API}/auth/login", json={"email": "ghost@example.com", "password": "Wrong123"})
    assert wrong_pw.status_code == 401 and no_user.status_code == 401
    assert wrong_pw.json() == no_user.json()


def test_refresh_token_rotation_and_reuse_detection(client, signup):
    old = signup("rot@example.com")["refresh"]

    r = client.post(f"{API}/auth/refresh", json={"refresh_token": old})
    assert r.status_code == 200
    new = r.json()["refresh_token"]
    assert new != old

    # the old token works only once; using it again looks like theft
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": old}).status_code == 401
    # ...so every token of that user is revoked, including the new one
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": new}).status_code == 401


def test_logout_revokes_refresh_token(client, signup):
    refresh = signup("out@example.com")["refresh"]
    assert client.post(f"{API}/auth/logout", json={"refresh_token": refresh}).status_code == 204
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": refresh}).status_code == 401


def test_expired_and_forged_access_tokens_are_rejected(client, signup):
    tokens = signup("tok@example.com")
    sub = jwt.decode(tokens["access"], settings.jwt_secret, algorithms=["HS256"])["sub"]
    now = datetime.now(timezone.utc)

    expired = jwt.encode(
        {"sub": sub, "role": "user", "iat": now - timedelta(hours=2), "exp": now - timedelta(hours=1)},
        settings.jwt_secret,
        algorithm="HS256",
    )
    forged = jwt.encode(
        {"sub": sub, "role": "user", "iat": now, "exp": now + timedelta(hours=1)},
        "another-secret-another-secret-123",
        algorithm="HS256",
    )
    for bad in (expired, forged):
        r = client.get(f"{API}/users/me", headers={"Authorization": f"Bearer {bad}"})
        assert r.status_code == 401
    assert client.get(f"{API}/users/me", headers=tokens["headers"]).status_code == 200


def test_login_is_rate_limited_per_email(client, signup):
    signup("brute@example.com")  # its login already used 1 of the 5 allowed tries per minute
    body = {"email": "brute@example.com", "password": "Wrong123"}
    codes = [client.post(f"{API}/auth/login", json=body).status_code for _ in range(5)]
    assert codes == [401, 401, 401, 401, 429]
    blocked = client.post(f"{API}/auth/login", json=body)
    assert blocked.status_code == 429
    assert "retry-after" in blocked.headers
