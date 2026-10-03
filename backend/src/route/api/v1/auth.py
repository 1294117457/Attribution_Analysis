"""认证路由 /api/v1/auth/*

公开端点：
- POST /register
- POST /login
- POST /refresh
- POST /send-verification-code
- GET  /captcha/generate

登录态端点：
- POST /logout
- GET  /me
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status

from application.service import AuthService
from infrastructure.config.di import get_auth_service
from infrastructure.security.captcha import Captcha
from route.api import _response as R
from route.api.v1.deps_auth import get_current_user_id
from route.dto.request.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    SendVerificationCodeRequest,
)
from route.dto.response.auth import (
    RefreshTokenResponse,
    TokenResponse,
    UserInfoResponse,
)  # noqa: F401  (CaptchaResponse 仅作为 schema 占位)


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


@router.post("/change-password", summary="用户自助修改密码（强制重登）")
async def change_password(
    req: ChangePasswordRequest,
    user_id: int = Depends(get_current_user_id),
    svc: AuthService = Depends(get_auth_service),
):
    """修改成功后撤销该用户全部 refresh token,前端需引导用户重新登录。"""
    await svc.change_password(user_id, req.old_password, req.new_password)
    return R.no_content("密码已修改,请重新登录")


@router.get("/me", summary="当前登录用户信息")
async def me(
    user_id: int = Depends(get_current_user_id),
    svc: AuthService = Depends(get_auth_service),
):
    info = await svc.get_user_info(user_id)
    return R.ok(info)