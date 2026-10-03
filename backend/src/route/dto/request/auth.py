"""认证授权 — Request DTO

按 DDD.md §2.3：DTO 是协议载体（JSON），与传输方式绑定，
统一放在 `route/dto/request/`。

注意：email 字段使用宽松的 str 类型（而不是 pydantic EmailStr），
以兼容 `admin@local`（无 TLD）这种开发环境的初始账号。
业务层会做基本的"含 @ 且长度合理"校验。
"""
from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# 简单邮箱格式：含 @ + 至少 1 字符 local + 至少 1 字符 domain
# 不强求 TLD,以兼容开发环境特殊账号
_EMAIL_LOOSE = re.compile(r"^[^@\s]+@[^@\s]+$")


def _validate_email_loose(v: str) -> str:
    """宽松的邮箱校验：保证非空 + 含 @ + 长度 ≤ 254 字符"""
    if not v or not isinstance(v, str):
        raise ValueError("email 不能为空")
    v = v.strip()
    if len(v) > 254:
        raise ValueError("email 过长")
    if not _EMAIL_LOOSE.match(v):
        raise ValueError("email 格式不正确(需含 @)")
    return v.lower()


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=8, max_length=64)
    nickname: Optional[str] = Field(None, max_length=64)
    code: str = Field(..., min_length=4, max_length=8, description="邮箱验证码")

    @field_validator("email")
    @classmethod
    def _check_email(cls, v: str) -> str:
        return _validate_email_loose(v)


class SendVerificationCodeRequest(BaseModel):
    email: str
    purpose: str = Field(
        default="register",
        description="用途:register / reset_password",
    )
    captcha_id: str = Field(..., min_length=1, description="图形验证码 ID(必填)")
    captcha_code: str = Field(..., min_length=1, description="图形验证码文字(必填,大小写不敏感)")

    @field_validator("email")
    @classmethod
    def _check_email(cls, v: str) -> str:
        return _validate_email_loose(v)


class LoginRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=8, max_length=64)
    captcha_id: str = Field(..., min_length=1, description="图形验证码 ID(必填)")
    captcha_code: str = Field(..., min_length=1, description="图形验证码文字(必填,大小写不敏感)")

    @field_validator("email")
    @classmethod
    def _check_email(cls, v: str) -> str:
        return _validate_email_loose(v)


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