"""认证路由 — 注册 / 发送邮箱验证码 /api/v1/auth/*

包含：
- POST /register                  注册新用户
- POST /send-verification-code    发送邮箱验证码（注册或找回密码通用）

密码相关（change-password / forgot-password）→ `auth_password.py`
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status

from contexts.auth.application.service.auth_service import AuthService
from contexts.auth.interface.dto.request.auth import (
    RegisterRequest,
    SendVerificationCodeRequest,
)
from contexts.auth.infrastructure.di import get_auth_service
from shared.interface import _response as R

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", summary="注册新用户", status_code=status.HTTP_201_CREATED)
async def register(
    req: RegisterRequest,
    request: Request,
    svc: AuthService = Depends(get_auth_service),
):
    """公开端点:邮箱 + 密码 + 邮箱验证码 + 可选昵称

    - 必须先调 POST /auth/send-verification-code 拿到 code
    - 自动绑定 member 角色
    - 通过邮箱验证码 = 邮箱已验证(is_verified=True)
    - 不会自动登录,前端需再调 /login
    """
    user = await svc.register(
        email=req.email,
        password=req.password,
        code=req.code,
        nickname=req.nickname,
    )
    return R.created({
        "id": user.id,
        "email": user.email,
        "nickname": user.nickname,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
    })


@router.post(
    "/send-verification-code", summary="发送邮箱验证码(必传图形验证码)"
)
async def send_verification_code(
    req: SendVerificationCodeRequest,
    request: Request,
    svc: AuthService = Depends(get_auth_service),
):
    """公开端点:发送 6 位数字验证码到邮箱。

    限流策略(同 email + purpose,Redis 实现):
    - 1 分钟内 1 次
    - 1 小时内 5 次

    图形验证码:必传(必须在 send-code 之前调 /auth/captcha/generate 拿到 captcha_id)。
    校验一次后立即失效(防重放)。
    """
    ua = request.headers.get("user-agent")
    ip = request.client.host if request.client else None
    info = await svc.send_verification_code(
        email=req.email,
        purpose=req.purpose,
        ip=ip,
        user_agent=ua,
        captcha_id=req.captcha_id,
        captcha_code=req.captcha_code,
    )
    return R.ok(info)
