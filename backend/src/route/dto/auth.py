"""认证授权 DTO

Request / Response 全部 Pydantic BaseModel,字段名 snake_case。
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ════════════════════════════════════════════════════════════════════════
# Request
# ════════════════════════════════════════════════════════════════════════


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=32)
    password: str = Field(..., min_length=8, max_length=64)
    nickname: Optional[str] = Field(None, max_length=64)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=64)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=8, max_length=64)
    new_password: str = Field(..., min_length=8, max_length=64)


class UpdateUserStatusRequest(BaseModel):
    is_active: bool


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=8, max_length=64)


class AssignRoleRequest(BaseModel):
    role_id: int = Field(..., ge=1)


# ════════════════════════════════════════════════════════════════════════
# Response
# ════════════════════════════════════════════════════════════════════════


class RoleBriefResponse(BaseModel):
    id: int
    code: str
    name: str


class UserInfoResponse(BaseModel):
    id: int
    email: str
    username: str
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    is_verified: bool
    roles: list[RoleBriefResponse]
    role_codes: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    created_at: Optional[str] = None
    last_login_at: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    user_info: Optional[UserInfoResponse] = None


class RefreshTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class UserListResponse(BaseModel):
    items: list[UserInfoResponse]
    total: int
    page: int
    page_size: int
    pages: int


class RoleResponse(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    is_system: bool
    sort_order: int


class PermissionResponse(BaseModel):
    id: int
    code: str
    resource: str
    action: str
    name: str
    description: Optional[str] = None