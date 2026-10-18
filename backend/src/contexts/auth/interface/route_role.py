"""角色路由 /api/v1/roles/* — 只读列表"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from contexts.auth.application.service.auth_service import AuthService
from contexts.auth.infrastructure.di import get_auth_service
from shared.interface import _response as R
from contexts.auth.interface.deps import require_permission


router = APIRouter(prefix="/roles", tags=["角色管理"])


@router.get("/", summary="角色列表（全部）")
async def list_roles(
    _user=Depends(require_permission("role:read")),
    svc: AuthService = Depends(get_auth_service),
):
    roles = await svc.list_roles()
    items = [
        {
            "id": r.id,
            "code": r.code,
            "name": r.name,
            "description": r.description,
            "is_system": r.is_system,
            "sort_order": r.sort_order,
        }
        for r in roles
    ]
    return R.ok(items)