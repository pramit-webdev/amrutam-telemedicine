from uuid import uuid4

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_totp_secret,
    hash_password,
    verify_password,
    verify_totp,
)


def test_hash_and_verify_password():
    pw = hash_password("test_password_123")
    assert isinstance(pw, str)
    assert len(pw) > 20
    assert verify_password("test_password_123", pw)
    assert not verify_password("wrong_password", pw)


def test_create_and_decode_access_token():
    user_id = uuid4()
    token = create_access_token(user_id, "patient")
    payload = decode_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["role"] == "patient"
    assert payload["type"] == "access"
    assert "jti" in payload
    assert "exp" in payload


def test_create_and_decode_refresh_token():
    user_id = uuid4()
    token = create_refresh_token(user_id)
    payload = decode_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "refresh"
    assert "jti" in payload
    assert "exp" in payload


def test_decode_invalid_token():
    payload = decode_token("invalid.token.here")
    assert payload == {}


def test_totp_generate_and_verify():
    secret = generate_totp_secret()
    assert len(secret) > 10
    token = "123456"
    result = verify_totp(secret, token)
    assert result is False
