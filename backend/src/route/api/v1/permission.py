"""权限路由 /api/v1/permissions/* — 只读列表"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from application.service import AuthService
from infrastructure.config.di import get_auth_service
from route.api import _response as R
from route.api.v1.deps_auth import require_permission


router = APIRouter(prefix="/permissions", tags=["权限管理"])


@router.get("/", summary="权限列表（全部）")
async def list_permissions(
    _user=Depends(require_permission("role:read")),
    svc: AuthService = Depends(get_auth_service),
):
    perms = await svc.list_permissions()
    items = [
        {
            "id": p.id,
            "code": p.code,
            "resource": p.resource,
            "action": p.action,
            "name": p.name,
            "description": p.description,
        }
        for p in perms
    ]
    return R.ok(items)