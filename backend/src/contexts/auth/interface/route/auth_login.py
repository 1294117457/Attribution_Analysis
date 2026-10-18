"""认证路由 — 登录/登出/me/刷新/验证码 /api/v1/auth/*

包含：
- POST /login                  登录
- POST /logout                 登出
- POST /refresh                刷新 token
- GET  /me                     当前登录用户信息
- GET  /captcha/generate       获取图形验证码

注册相关（register / send-verification-code）→ `auth_register.py`
密码相关（change-password / forgot-password）→ `auth_password.py`
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from contexts.auth.application.service.auth_service import AuthService
from contexts.auth.interface.deps import get_current_user_id
from contexts.auth.interface.dto.request.auth import (
    LoginRequest,
    RefreshTokenRequest,
)
from contexts.auth.interface.dto.response.auth import (
    RefreshTokenResponse,
    TokenResponse,
    UserInfoResponse,
)  # noqa: F401  (CaptchaResponse 仅作为 schema 占位)
from contexts.auth.infrastructure.di import get_auth_service
from contexts.auth.infrastructure.security.captcha import Captcha
from shared.interface import _response as R

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", summary="登录(必传图形验证码)")
async def login(
    req: LoginRequest,
    request: Request,
    svc: AuthService = Depends(get_auth_service),
):
    """返回双 token + user_info。

    图形验证码:必传(必须在 login 之前调 /auth/captcha/generate 拿到 captcha_id)。
    校验一次后立即失效(防重放)。
    """
    ua = request.headers.get("user-agent")
    ip = request.client.host if request.client else None
    data = await svc.login(
        email=req.email,
        password=req.password,
        user_agent=ua,
        ip=ip,
        captcha_id=req.captcha_id,
        captcha_code=req.captcha_code,
    )
    return R.ok({
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "token_type": data["token_type"],
        "expires_in": data["expires_in"],
        "user_info": data["user_info"],
    })


@router.post("/refresh", summary="刷新 token（rotation）")
async def refresh(
    req: RefreshTokenRequest,
    svc: AuthService = Depends(get_auth_service),
):
    """旧 refresh_token 一次性使用,失败不重试。"""
    data = await svc.refresh_token(req.refresh_token)
    return R.ok({
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "token_type": data["token_type"],
        "expires_in": data["expires_in"],
    })


@router.post("/logout", summary="登出")
async def logout(
    user_id: int = Depends(get_current_user_id),
    svc: AuthService = Depends(get_auth_service),
):
    """撤销该用户全部未撤销的 refresh token(access token 短效,自然到期)。"""
    await svc.logout(user_id)
    return R.no_content("已登出")


@router.get(
    "/captcha/generate",
    summary="获取图形验证码",
)
async def generate_captcha():
    """获取一张 4 位字母+数字图形验证码,有效期 5 分钟(一次性)。

    - 前端拿到 base64 后渲染到 <img>,用户在提交时一并回传 captcha_id + 输入文字
    - 测试旁路:输入 '0000' 可绕过任意 captcha_id
    """
    captcha_id, base64_image = await Captcha.generate()
    return R.ok({
        "captcha_id": captcha_id,
        "base64": f"data:image/png;base64,{base64_image}",
    })


@router.get("/me", summary="当前登录用户信息")
async def me(
    user_id: int = Depends(get_current_user_id),
    svc: AuthService = Depends(get_auth_service),
):
    info = await svc.get_user_info(user_id)
    return R.ok(info)
