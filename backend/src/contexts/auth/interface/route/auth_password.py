"""认证路由 — 改密 / 找回密码 /api/v1/auth/*

包含：
- POST /change-password              登录后自助改密
- POST /forgot-password/send-code    找回密码 Step 1: 验证图形码 + 发邮箱码
- POST /forgot-password/reset        找回密码 Step 2: 校验邮箱码 + 设新密码
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from contexts.auth.application.service.auth_service import AuthService
from contexts.auth.interface.deps import get_current_user_id
from contexts.auth.interface.dto.request.auth import (
    ChangePasswordRequest,
    ForgotPasswordResetRequest,
    ForgotPasswordSendCodeRequest,
)
from contexts.auth.infrastructure.di import get_auth_service
from shared.interface import _response as R

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/change-password", summary="用户自助修改密码（强制重登）")
async def change_password(
    req: ChangePasswordRequest,
    user_id: int = Depends(get_current_user_id),
    svc: AuthService = Depends(get_auth_service),
):
    """修改成功后撤销该用户全部 refresh token,前端需引导用户重新登录。"""
    await svc.change_password(user_id, req.old_password, req.new_password)
    return R.no_content("密码已修改,请重新登录")


@router.post(
    "/forgot-password/send-code",
    summary="找回密码 Step 1：发送邮箱验证码(必传图形验证码)",
)
async def forgot_password_send_code(
    req: ForgotPasswordSendCodeRequest,
    request: Request,
    svc: AuthService = Depends(get_auth_service),
):
    """找回密码流程第一步:验证图形验证码 + 校验邮箱已注册 → 发送 6 位邮箱验证码。

    错误细分:
    - 图形验证码错 → CAPTCHA_INVALID（前端可据此高亮图形验证码）
    - 邮箱未注册   → ACCOUNT_NOT_FOUND（提示用户去注册）
    - 限流         → EMAIL_CODE_RATE_LIMITED
    """
    ua = request.headers.get("user-agent")
    ip = request.client.host if request.client else None
    info = await svc.forgot_password_send_code(
        email=req.email,
        ip=ip,
        user_agent=ua,
        captcha_id=req.captcha_id,
        captcha_code=req.captcha_code,
    )
    return R.ok(info)


@router.post(
    "/forgot-password/reset",
    summary="找回密码 Step 2：校验邮箱验证码 + 设置新密码",
)
async def forgot_password_reset(
    req: ForgotPasswordResetRequest,
    svc: AuthService = Depends(get_auth_service),
):
    """找回密码流程第二步:校验邮箱验证码 + 写入新密码。

    成功后撤销该用户全部 refresh token（强制其他设备重登），不会自动登录，
    前端引导用户去 /login 用新密码登录。

    错误细分:
    - 邮箱验证码错 / 过期 → EMAIL_CODE_INVALID / EMAIL_CODE_EXPIRED
    - 账号不存在          → ACCOUNT_NOT_FOUND
    """
    await svc.forgot_password_reset(
        email=req.email,
        code=req.code,
        new_password=req.new_password,
    )
    return R.no_content("密码已重置，请使用新密码登录")
