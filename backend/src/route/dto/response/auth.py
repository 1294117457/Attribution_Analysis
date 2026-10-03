"""认证授权 — Response DTO

按 DDD.md §2.3：DTO 放在 `route/dto/response/`。
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class RoleBriefResponse(BaseModel):
    id: int
    code: str
    name: str


class UserInfoResponse(BaseModel):
    id: int
    email: str
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


class CaptchaResponse(BaseModel):
    """图形验证码返回(前端用于渲染 + 提交时回填)"""

    captcha_id: str = Field(..., description="图形验证码 ID(提交时回传)")
    base64: str = Field(..., description="data:image/png;base64,xxx")


__all__ = [
    "RoleBriefResponse",
    "UserInfoResponse",
    "TokenResponse",
    "RefreshTokenResponse",
    "UserListResponse",
    "RoleResponse",
    "PermissionResponse",
    "CaptchaResponse",
]