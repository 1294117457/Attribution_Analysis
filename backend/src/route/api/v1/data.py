"""数据接口直调 API：按名调用任意 Port（经 DataQueryService，不入库）

这些接口消耗 tushare 积分和同花顺 IP 配额，需登录鉴权。
要"采集并入库"请走 /collect/tasks。
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from application.port.data.base import InvalidParams, NotSupported, RateLimited, SourceUnavailable
from application.service.data_query_service import DataQueryService
from infrastructure.config.di import get_data_query_service
from route.api import _response as R
from route.api.v1.deps_auth import require_permission

router = APIRouter(prefix="/data", tags=["数据接口"])


class DataQueryRequest(BaseModel):
    params: dict[str, Any] = Field(default_factory=dict, description="接口参数，见 /data/catalog 的 params_schema")
    source: Optional[str] = Field(None, description="指定实现（tool），如 tushare；为空按优先级自动选择")


@router.get("/catalog", summary="数据接口目录（全部 Port + 参数 schema + 可用实现）")
async def data_catalog(
    svc: DataQueryService = Depends(get_data_query_service),
    _user=Depends(require_permission("data:query")),
):
    return R.ok([p.to_dict() for p in svc.catalog()])


@router.post("/{name}", summary="按名调用数据接口")
async def data_query(
    name: str,
    body: DataQueryRequest,
    svc: DataQueryService = Depends(get_data_query_service),
    _user=Depends(require_permission("data:query")),
):
    if not svc.has(name):
        return R.err(f"未知数据接口: {name}", 404)
    try:
        res = await svc.query(name, body.params, source=body.source)
    except InvalidParams as e:
        return R.err(str(e), 422)
    except NotSupported as e:
        return R.err(str(e), 400)
    except (RateLimited, SourceUnavailable) as e:
        return JSONResponse(status_code=503, content={
            "code": 503,
            "message": str(e),
            "data": {"attempts": [list(a) for a in e.attempts]},
        })
    return R.ok(res.to_dict())
