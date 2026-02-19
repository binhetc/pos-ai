"""Dependency injection: auth middleware, RBAC enforcement, store context."""

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from app.core.security import decode_access_token
from app.schemas.auth import CurrentUser

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> CurrentUser:
    """Decode JWT and return CurrentUser. Raises 401 on invalid/expired token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return CurrentUser(
            id=UUID(user_id),
            email="",  # lightweight — full profile via /me endpoint
            full_name="",
            role=payload["role"],
            store_id=UUID(payload["store_id"]),
            permissions=payload.get("permissions", []),
            is_active=True,
        )
    except (JWTError, KeyError, ValueError):
        raise credentials_exception


def require_permission(*required: str):
    """Dependency factory: checks the user has ALL required permissions."""

    async def checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        missing = [p for p in required if p not in user.permissions]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permissions: {', '.join(missing)}",
            )
        return user

    return checker


def require_role(*allowed_roles: str):
    """Dependency factory: checks the user has one of the allowed roles."""

    async def checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' not allowed. Required: {', '.join(allowed_roles)}",
            )
        return user

    return checker


class StoreContext:
    """Extracts store_id from current user token — ensures every query is scoped to user's store."""

    def __init__(self, user: CurrentUser = Depends(get_current_user)):
        self.store_id: UUID = user.store_id
        self.user_id: UUID = user.id
        self.role: str = user.role
        self.permissions: list[str] = user.permissions
