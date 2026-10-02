"""认证路由 /api/v1/auth/*

公开端点：
- POST /register
- POST /login
- POST /refresh

登录态端点：
- POST /logout
- GET  /me
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status

from application.service.auth_app_service import AuthAppService
from infrastructure.config.di import get_auth_app_service
from route.api import _response as R
from route.api.v1.deps_auth import get_current_user_id
from route.dto.auth import (
    LoginRequest,
    RefreshTokenRequest,
    RefreshTokenResponse,
    RegisterRequest,
    TokenResponse,
    UserInfoResponse,
)


router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", summary="注册新用户", status_code=status.HTTP_201_CREATED)
async def register(
    req: RegisterRequest,
    svc: AuthAppService = Depends(get_auth_app_service),
):
    """公开端点:邮箱 + 用户名 + 密码 + 可选昵称

    - 自动绑定 member 角色
    - 不会自动登录,前端需再调 /login
    """
    user = await svc.register(
        email=req.email,
        username=req.username,
        password=req.password,
        nickname=req.nickname,
    )
    return R.created({
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "nickname": user.nickname,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
    })


@router.post("/login", summary="登录")
async def login(
    req: LoginRequest,
    request: Request,
    svc: AuthAppService = Depends(get_auth_app_service),
):
    """返回双 token + user_info。"""
    ua = request.headers.get("user-agent")
    ip = request.client.host if request.client else None
    data = await svc.login(
        email=req.email,
        password=req.password,
        user_agent=ua,
        ip=ip,
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
    svc: AuthAppService = Depends(get_auth_app_service),
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
    svc: AuthAppService = Depends(get_auth_app_service),
):
    """撤销该用户全部未撤销的 refresh token(access token 短效,自然到期)。"""
    await svc.logout(user_id)
    return R.no_content("已登出")


@router.get("/me", summary="当前登录用户信息")
async def me(
    user_id: int = Depends(get_current_user_id),
    svc: AuthAppService = Depends(get_auth_app_service),
):
    info = await svc.get_user_info(user_id)
    return R.ok(info)