"""catalog — service 元数据 catalog 路由

提供：
    GET /collect/catalog     service 元数据 catalog（主路径）
    GET /collect/services    同上（兼容旧路径，deprecated）
    GET /collect/query/{name} 实时查询 service.get()

Phase 2 重构（2026-10-19）：
    - 从 manage/ 迁入 route/catalog.py
    - 每个采集 service 直接对应自己的路由，无中间触发器
"""
from __future__ import annotations

import json as _json
from typing import Any

from fastapi import APIRouter, HTTPException

from shared.interface import _response as R
from contexts.collect.application.service.manage import CatalogService

router = APIRouter(prefix="/collect", tags=["采集-管理面"])
_svc = CatalogService()


@router.get(
    "/catalog",
    summary="service 元数据 catalog（前端左侧目录树数据源）",
    response_description="{ total, items: [...] }",
)
async def list_catalog() -> dict[str, Any]:
    """列出全部 service 的元数据

    响应 data: { total, items: [{name, facet, label, description,
                                 kind, supports_query, path, query_path}, ...] }
    """
    items = _svc.list()
    return R.ok({"total": len(items), "items": items})


@router.get(
    "/services",
    summary="[deprecated] service 元数据 catalog — 请改用 /collect/catalog",
    response_description="同 /collect/catalog",
    deprecated=True,
)
async def list_services() -> dict[str, Any]:
    """[已废弃] /collect/services — 旧路径兼容

    新路径是 /collect/catalog。/services 名字容易误以为是"拉 service 实例"，
    实际返回的是 catalog 聚合元数据，故改名。
    """
    items = _svc.list()
    return R.ok({"total": len(items), "items": items})


@router.get(
    "/query/{service_name}",
    summary="实时查询 service.get()",
    response_description="list[dict]（service 决定）",
)
async def query_service(
    service_name: str,
    params: str = "",  # JSON-encoded kwargs；留空表示无参数
) -> dict[str, Any]:
    """对 supports_query=true 的 service 调 get(**kwargs)

    入参用 query string `params=<JSON>`，例如：
        ?params={"symbol":"000001","interval":"5","days":1}
    """
    meta = _svc.get(service_name)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"service {service_name!r} 不存在")
    if not meta.get("supports_query"):
        raise HTTPException(
            status_code=400,
            detail=f"service {service_name!r} 不支持实时查询（supports_query=false）",
        )

    if params.strip():
        try:
            kwargs = _json.loads(params)
        except _json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"params 不是合法 JSON: {e}")
        if not isinstance(kwargs, dict):
            raise HTTPException(status_code=400, detail="params 必须是 JSON object")
    else:
        kwargs = {}

    cls = _svc.get_class(service_name)
    instance = cls()  # 无状态 default construct
    try:
        result = await instance.get(**kwargs)
    except TypeError as e:
        raise HTTPException(status_code=400, detail=f"参数错误: {e}")
    return R.ok(result)


__all__ = ["router"]
