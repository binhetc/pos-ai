"""Unit tests for auth: security utils + dependency logic."""

import uuid
from datetime import timedelta

import pytest
from jose import jwt

from app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from app.core.config import settings


# ── Password hashing ──────────────────────────────

def test_hash_and_verify():
    plain = "SecurePass123!"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed)
    assert not verify_password("wrong", hashed)


# ── JWT ────────────────────────────────────────────

def test_create_and_decode_token():
    uid = uuid.uuid4()
    sid = uuid.uuid4()
    token = create_access_token(
        user_id=uid,
        store_id=sid,
        role="owner",
        permissions=["product:read", "order:create"],
    )
    payload = decode_access_token(token)
    assert payload["sub"] == str(uid)
    assert payload["store_id"] == str(sid)
    assert payload["role"] == "owner"
    assert "product:read" in payload["permissions"]


def test_expired_token():
    token = create_access_token(
        user_id=uuid.uuid4(),
        store_id=uuid.uuid4(),
        role="cashier",
        permissions=[],
        expires_delta=timedelta(seconds=-1),
    )
    with pytest.raises(Exception):
        decode_access_token(token)


# ── Permission matrix sanity ──────────────────────

def test_rbac_matrix():
    from app.db.seed_rbac import ROLE_PERMISSIONS
    from app.models.role import RoleType, PermissionAction

    # Owner has ALL permissions
    assert set(ROLE_PERMISSIONS[RoleType.OWNER]) == set(PermissionAction)

    # Cashier subset of Manager subset of Owner
    cashier = set(ROLE_PERMISSIONS[RoleType.CASHIER])
    manager = set(ROLE_PERMISSIONS[RoleType.MANAGER])
    owner = set(ROLE_PERMISSIONS[RoleType.OWNER])
    assert cashier <= manager <= owner  # strict subset chain
