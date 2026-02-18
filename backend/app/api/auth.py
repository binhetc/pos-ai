"""Authentication endpoints: login + register store owner."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import hash_password, verify_password, create_access_token
from app.core.deps import get_current_user
from app.db.base import get_db
from app.models.user import User
from app.models.store import Store
from app.models.role import Role, RoleType, Permission, RolePermission
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    RegisterOwnerRequest,
    RegisterOwnerResponse,
    CurrentUser,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate via email + password, return JWT."""
    result = await db.execute(
        select(User)
        .where(User.email == body.email)
        .options(
            selectinload(User.role).selectinload(Role.permissions).selectinload(RolePermission.permission)
        )
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    permissions = [rp.permission.action.value for rp in user.role.permissions]
    token = create_access_token(
        user_id=user.id,
        store_id=user.store_id,
        role=user.role.name.value,
        permissions=permissions,
    )
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        store_id=user.store_id,
        role=user.role.name.value,
    )


@router.post(
    "/register",
    response_model=RegisterOwnerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_owner(body: RegisterOwnerRequest, db: AsyncSession = Depends(get_db)):
    """Register a new store with an owner account (self-service onboarding)."""

    # Check duplicate email
    existing_user = await db.execute(select(User).where(User.email == body.email))
    if existing_user.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    # Check duplicate store code
    existing_store = await db.execute(select(Store).where(Store.code == body.store_code))
    if existing_store.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Store code already taken")

    # Get or create owner role
    role_result = await db.execute(
        select(Role)
        .where(Role.name == RoleType.OWNER)
        .options(selectinload(Role.permissions).selectinload(RolePermission.permission))
    )
    owner_role = role_result.scalar_one_or_none()
    if not owner_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RBAC roles not seeded. Run seed_rbac first.",
        )

    # Create store
    store = Store(
        name=body.store_name,
        code=body.store_code,
        address=body.store_address,
        phone=body.store_phone,
    )
    db.add(store)
    await db.flush()  # get store.id

    # Create owner user
    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        phone=body.phone,
        store_id=store.id,
        role_id=owner_role.id,
    )
    db.add(user)
    await db.flush()  # get user.id

    permissions = [rp.permission.action.value for rp in owner_role.permissions]
    token = create_access_token(
        user_id=user.id,
        store_id=store.id,
        role=RoleType.OWNER.value,
        permissions=permissions,
    )

    return RegisterOwnerResponse(
        user_id=user.id,
        store_id=store.id,
        access_token=token,
    )


@router.get("/me", response_model=CurrentUser)
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return full profile of the current authenticated user."""
    result = await db.execute(
        select(User)
        .where(User.id == current_user.id)
        .options(
            selectinload(User.role).selectinload(Role.permissions).selectinload(RolePermission.permission)
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return CurrentUser(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.name.value,
        store_id=user.store_id,
        permissions=[rp.permission.action.value for rp in user.role.permissions],
        is_active=user.is_active,
    )
