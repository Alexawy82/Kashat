"""
JWT Authentication Module for LedgerLoop

Provides:
- JWT token creation and validation
- Password hashing with bcrypt
- User management (single-user mode for now)
- FastAPI dependencies for protected routes
"""

from __future__ import annotations

import os
import uuid
import json
from datetime import datetime, timedelta, UTC
from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from jose import JWTError, jwt
from passlib.context import CryptContext

from ..db import get_conn


# Configuration
JWT_SECRET_KEY = os.getenv("LEDGERLOOP_JWT_SECRET", "ledgerloop-dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security scheme for Bearer tokens
security = HTTPBearer(auto_error=False)


# ============================================================================
# Password Utilities
# ============================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


# ============================================================================
# Token Utilities
# ============================================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "access"
    })
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "refresh",
        "jti": str(uuid.uuid4())  # Unique ID for token revocation
    })
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


# ============================================================================
# User Management
# ============================================================================

def _ensure_user_table():
    """Ensure the user table exists in the database."""
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS app_user (
            id VARCHAR PRIMARY KEY,
            username VARCHAR UNIQUE NOT NULL,
            password_hash VARCHAR NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            must_change_password BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP),
            last_login TIMESTAMP
        )
    """)

    # Create token blacklist table for logout functionality
    conn.execute("""
        CREATE TABLE IF NOT EXISTS token_blacklist (
            jti VARCHAR PRIMARY KEY,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP)
        )
    """)


def _ensure_default_user():
    """Create default admin user if no users exist."""
    _ensure_user_table()
    conn = get_conn()

    # Check if any user exists
    count = conn.execute("SELECT COUNT(*) FROM app_user").fetchone()[0]
    if count == 0:
        # Create default admin user
        user_id = str(uuid.uuid4())
        password_hash = get_password_hash("adminadmin")
        conn.execute(
            """INSERT INTO app_user (id, username, password_hash, must_change_password)
               VALUES (?, ?, ?, ?)""",
            [user_id, "admin", password_hash, True]
        )
        # Log the creation
        try:
            conn.execute(
                """INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                [str(uuid.uuid4()), "user", user_id, "create_default",
                 json.dumps({"username": "admin"}), datetime.now(UTC), "system"]
            )
        except Exception:
            pass


def get_user_by_username(username: str) -> Optional[dict]:
    """Get user by username."""
    _ensure_user_table()
    conn = get_conn()
    row = conn.execute(
        """SELECT id, username, password_hash, is_active, must_change_password, created_at, last_login
           FROM app_user WHERE username = ?""",
        [username]
    ).fetchone()

    if row:
        return {
            "id": row[0],
            "username": row[1],
            "password_hash": row[2],
            "is_active": row[3],
            "must_change_password": row[4],
            "created_at": row[5],
            "last_login": row[6]
        }
    return None


def get_user_by_id(user_id: str) -> Optional[dict]:
    """Get user by ID."""
    _ensure_user_table()
    conn = get_conn()
    row = conn.execute(
        """SELECT id, username, password_hash, is_active, must_change_password, created_at, last_login
           FROM app_user WHERE id = ?""",
        [user_id]
    ).fetchone()

    if row:
        return {
            "id": row[0],
            "username": row[1],
            "password_hash": row[2],
            "is_active": row[3],
            "must_change_password": row[4],
            "created_at": row[5],
            "last_login": row[6]
        }
    return None


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Authenticate user with username and password."""
    _ensure_default_user()
    user = get_user_by_username(username)
    if not user:
        return None
    if not user["is_active"]:
        return None
    if not verify_password(password, user["password_hash"]):
        return None

    # Update last login
    conn = get_conn()
    conn.execute(
        "UPDATE app_user SET last_login = ? WHERE id = ?",
        [datetime.now(UTC), user["id"]]
    )

    return user


def update_user_password(user_id: str, new_password: str) -> bool:
    """Update user password and clear must_change_password flag."""
    conn = get_conn()
    password_hash = get_password_hash(new_password)
    result = conn.execute(
        """UPDATE app_user SET password_hash = ?, must_change_password = FALSE
           WHERE id = ?""",
        [password_hash, user_id]
    )

    # Log password change
    try:
        conn.execute(
            """INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [str(uuid.uuid4()), "user", user_id, "change_password",
             json.dumps({}), datetime.now(UTC), user_id]
        )
    except Exception:
        pass

    return True


def create_user(username: str, password: str, created_by: str = "system") -> Optional[dict]:
    """Create a new user account."""
    _ensure_user_table()
    conn = get_conn()

    # Check if username already exists
    existing = get_user_by_username(username)
    if existing:
        return None

    # Create user
    user_id = str(uuid.uuid4())
    password_hash = get_password_hash(password)
    conn.execute(
        """INSERT INTO app_user (id, username, password_hash, must_change_password)
           VALUES (?, ?, ?, ?)""",
        [user_id, username, password_hash, False]
    )

    # Log creation
    try:
        conn.execute(
            """INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [str(uuid.uuid4()), "user", user_id, "create_user",
             json.dumps({"username": username}), datetime.now(UTC), created_by]
        )
    except Exception:
        pass

    return get_user_by_id(user_id)


def is_registration_enabled() -> bool:
    """Check if public registration is enabled."""
    return os.getenv("LEDGERLOOP_ALLOW_REGISTRATION", "false").lower() in ("true", "1", "yes")


# ============================================================================
# Token Blacklist (for logout)
# ============================================================================

def blacklist_token(jti: str, expires_at: datetime):
    """Add a token to the blacklist."""
    _ensure_user_table()
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO token_blacklist (jti, expires_at) VALUES (?, ?) ON CONFLICT DO NOTHING",
            [jti, expires_at]
        )
    except Exception:
        pass


def is_token_blacklisted(jti: str) -> bool:
    """Check if a token is blacklisted."""
    _ensure_user_table()
    conn = get_conn()
    row = conn.execute(
        "SELECT 1 FROM token_blacklist WHERE jti = ?",
        [jti]
    ).fetchone()
    return row is not None


def cleanup_expired_blacklist():
    """Remove expired tokens from blacklist."""
    _ensure_user_table()
    conn = get_conn()
    conn.execute(
        "DELETE FROM token_blacklist WHERE expires_at < ?",
        [datetime.now(UTC)]
    )


# ============================================================================
# FastAPI Dependencies
# ============================================================================

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """
    Dependency to get the current authenticated user.

    Extracts JWT from Authorization: Bearer header, validates it,
    and returns the user dict or raises 401.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials:
        raise credentials_exception

    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        raise credentials_exception

    # Check token type
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if token is blacklisted (for refresh tokens mainly, but check anyway)
    jti = payload.get("jti")
    if jti and is_token_blacklisted(jti):
        raise credentials_exception

    # Get user
    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = get_user_by_id(user_id)
    if user is None:
        raise credentials_exception

    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled"
        )

    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """
    Optional authentication - returns user if authenticated, None otherwise.
    Useful for endpoints that work with or without authentication.
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


# ============================================================================
# Legacy compatibility functions
# ============================================================================

def require_admin(request: Request):
    """Legacy admin check - now a no-op, use get_current_user dependency instead."""
    return True


def require_api(request: Request):
    """Legacy API check - now a no-op, use get_current_user dependency instead."""
    return True
