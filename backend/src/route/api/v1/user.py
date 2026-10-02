"""用户管理路由 /api/v1/users/*

均需 user:read / user:write 权限。
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from application.service.auth_app_service import AuthAppService
from infrastructure.config.di import get_auth_app_service
from route.api import _response as R
from route.api.v1.deps_auth import require_permission
from route.dto.auth import (
    AssignRoleRequest,
    ResetPasswordRequest,
    UpdateUserStatusRequest,
    UserListResponse,
)


router = APIRouter(prefix="/users", tags=["用户管理"])


@router.get(
    "/",
    summary="用户列表（分页 / 搜索 / 状态筛选）",
)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: Optional[str] = Query(None, description="邮箱 / 用户名 / 昵称模糊搜索"),
    is_active: Optional[bool] = Query(None, description="按是否启用筛选"),
    _user=Depends(require_permission("user:read")),
    svc: AuthAppService = Depends(get_auth_app_service),
):
    items, total = await svc.list_users(
        page=page,
        page_size=page_size,
        keyword=keyword,
        is_active=is_active,
    )
    pages = (total + page_size - 1) // page_size
    return R.ok({
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    })


@router.patch("/{user_id}/status", summary="启用 / 禁用用户")
async def update_status(
    user_id: int,
    req: UpdateUserStatusRequest,
    _user=Depends(require_permission("user:write")),
    svc: AuthAppService = Depends(get_auth_app_service),
):
    result = await svc.update_user_status(user_id, req.is_active)
    return R.ok(result)


@router.post("/{user_id}/reset-password", summary="重置用户密码（强制重登）")
async def reset_password(
    user_id: int,
    req: ResetPasswordRequest,
    _user=Depends(require_permission("user:write")),
    svc: AuthAppService = Depends(get_auth_app_service),
):
    await svc.reset_user_password(user_id, req.new_password)
    return R.no_content("密码已重置,该用户全部设备将自动下线")


@router.post("/{user_id}/roles", summary="分配角色给用户（幂等）")
async def assign_role(
    user_id: int,
    req: AssignRoleRequest,
    _user=Depends(require_permission("user:write")),
    svc: AuthAppService = Depends(get_auth_app_service),
):
    await svc.assign_role(user_id, req.role_id)
    return R.no_content("已分配")


@router.delete("/{user_id}/roles/{role_id}", summary="解除用户角色（幂等）")
async def remove_role(
    user_id: int,
    role_id: int,
    _user=Depends(require_permission("user:write")),
    svc: AuthAppService = Depends(get_auth_app_service),
):
    await svc.remove_role(user_id, role_id)
    return R.no_content("已解除")