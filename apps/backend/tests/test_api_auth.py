import asyncio
import importlib
from datetime import datetime, timedelta, UTC

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials


def _load_auth():
    import kashat.api.auth as auth
    importlib.reload(auth)
    return auth


def test_auth_user_flow_and_tokens(db_conn):
    auth = _load_auth()

    user = auth.create_user("alice", "secret")
    assert user is not None
    assert user["username"] == "alice"

    assert auth.authenticate_user("alice", "secret") is not None
    assert auth.authenticate_user("alice", "wrong") is None

    assert auth.update_user_password(user["id"], "newpass")
    assert auth.authenticate_user("alice", "newpass") is not None

    access = auth.create_access_token({"sub": user["id"]})
    access_payload = auth.decode_token(access)
    assert access_payload["sub"] == user["id"]
    assert access_payload["type"] == "access"

    refresh = auth.create_refresh_token({"sub": user["id"]})
    refresh_payload = auth.decode_token(refresh)
    assert refresh_payload["type"] == "refresh"
    assert refresh_payload.get("jti")

    auth.blacklist_token(refresh_payload["jti"], datetime.now(UTC) + timedelta(days=1))
    assert auth.is_token_blacklisted(refresh_payload["jti"]) is True

    expired = f"{refresh_payload['jti']}-expired"
    auth.blacklist_token(expired, datetime.now(UTC) - timedelta(days=1))
    auth.cleanup_expired_blacklist()
    assert auth.is_token_blacklisted(expired) is False


def test_auth_dependencies_and_flags(db_conn, monkeypatch):
    auth = _load_auth()

    admin = auth.authenticate_user("admin", "adminadmin")
    assert admin is not None

    token = auth.create_access_token({"sub": admin["id"]})
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    current = asyncio.run(auth.get_current_user(creds))
    assert current["id"] == admin["id"]

    refresh = auth.create_refresh_token({"sub": admin["id"]})
    with pytest.raises(HTTPException):
        asyncio.run(auth.get_current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials=refresh)))

    assert asyncio.run(auth.get_current_user_optional(None)) is None

    monkeypatch.setenv("LEDGERLOOP_ALLOW_REGISTRATION", "true")
    assert auth.is_registration_enabled() is True
    monkeypatch.setenv("LEDGERLOOP_ALLOW_REGISTRATION", "false")
    assert auth.is_registration_enabled() is False

    assert auth.require_admin(None) is True
    assert auth.require_api(None) is True
