"""Auth request/response schemas."""

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ── Login ──────────────────────────────────────────
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    store_id: UUID
    role: str


# ── Register Store Owner ───────────────────────────
class RegisterOwnerRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1, max_length=255)
    phone: str | None = None
    store_name: str = Field(min_length=1, max_length=255)
    store_code: str = Field(min_length=1, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    store_address: str | None = None
    store_phone: str | None = None


class RegisterOwnerResponse(BaseModel):
    user_id: UUID
    store_id: UUID
    access_token: str
    token_type: str = "bearer"
    message: str = "Store owner registered successfully"


# ── Current User ───────────────────────────────────
class CurrentUser(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str
    store_id: UUID
    permissions: list[str]
    is_active: bool
