import uuid

import jwt
import pytest

from app.core.security import (
    create_access_token, decode_access_token, hash_password,
    hash_refresh_token, verify_password,
)


def test_password_roundtrip():
    h = hash_password("Secret123")
    assert h != "Secret123"
    assert verify_password("Secret123", h)
    assert not verify_password("wrong", h)


def test_jwt_roundtrip():
    uid = uuid.uuid4()
    payload = decode_access_token(create_access_token(uid, "user"))
    assert payload["sub"] == str(uid)


def test_tampered_jwt_rejected():
    token = create_access_token(uuid.uuid4()) + "x"
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(token)


def test_refresh_hash_is_stable():
    assert hash_refresh_token("abc") == hash_refresh_token("abc")
