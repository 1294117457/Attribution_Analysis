"""认证授权 - FastAPI 依赖

提供:
- get_current_user_id:  解析 Bearer token,返回 user_id(整型)
- get_current_user:     返回 user 完整 dict(roles+permissions)
- require_role(...):     工厂,要求用户拥有任一指定 role_code
- require_permission(...): 工厂,要求用户拥有任一指定 permission_code
"""
from __future__ import annotations

from typing import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from application.service.auth_app_service import AuthAppService
from infrastructure.config.di import get_db


security = HTTPBearer(auto_error=False)


async def get_current_user_id(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    session: AsyncSession = Depends(get_db),
) -> int:
    """解析 Bearer access token,返回 user_id;将 claims 写入 request.state。"""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    svc = AuthAppService(session)
    try:
        claims = await svc.parse_access_token(token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e.message) if hasattr(e, "message") else str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 写入 request.state,后续日志 / 中间件可用
    request.state.token_claims = claims
    request.state.user_id = int(claims["sub"])
    return int(claims["sub"])


async def get_current_user(
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """返回完整 user dict(由应用服务组装,含 roles + permissions)。"""
    svc = AuthAppService(session)
    return await svc.get_user_info(user_id)


def require_role(*required_roles: str) -> Callable:
    """依赖工厂:用户必须拥有任一 required role。"""

    async def _checker(user: dict = Depends(get_current_user)) -> dict:
        codes = set(user.get("role_codes", []))
        if not codes.intersection(required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要角色之一: {', '.join(required_roles)}",
            )
        return user

    return _checker


def require_permission(*required_perms: str) -> Callable:
    """依赖工厂:用户必须拥有任一 required permission。"""

    async def _checker(user: dict = Depends(get_current_user)) -> dict:
        perms = set(user.get("permissions", []))
        if not perms.intersection(required_perms):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要权限之一: {', '.join(required_perms)}",
            )
        return user

    return _checker