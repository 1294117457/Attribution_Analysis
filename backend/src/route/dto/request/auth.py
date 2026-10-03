"""认证授权 — Request DTO

按 DDD.md §2.3：DTO 是协议载体（JSON），与传输方式绑定，
统一放在 `route/dto/request/`。
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=64)
    nickname: Optional[str] = Field(None, max_length=64)
    code: str = Field(..., min_length=4, max_length=8, description="邮箱验证码")


class SendVerificationCodeRequest(BaseModel):
    email: EmailStr
    purpose: str = Field(
        default="register",
        description="用途:register / reset_password",
    )
    captcha_id: str = Field(..., min_length=1, description="图形验证码 ID(必填)")
    captcha_code: str = Field(..., min_length=1, description="图形验证码文字(必填,大小写不敏感)")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=64)
    captcha_id: str = Field(..., min_length=1, description="图形验证码 ID(必填)")
    captcha_code: str = Field(..., min_length=1, description="图形验证码文字(必填,大小写不敏感)")


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


__all__ = [
    "RegisterRequest",
    "SendVerificationCodeRequest",
    "LoginRequest",
    "RefreshTokenRequest",
    "ChangePasswordRequest",
    "UpdateUserStatusRequest",
    "ResetPasswordRequest",
    "AssignRoleRequest",
]