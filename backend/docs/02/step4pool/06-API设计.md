# 操作池 - API 设计

> 本文档定义"操作池"模块的 REST API 路由设计。
>
> **响应格式**：统一遵循 `{code, message, data}` 结构。

---

## 1. API 概览

### 1.1 路由分组

| 前缀 | 标签 | 说明 |
|------|------|------|
| `/api/v1/pools` | Pool | 池管理 + 成员管理 |
| `/api/v1/pools/{pool_id}/operations` | Pool Operation | 池级操作 |
| `/api/v1/operations/{op_id}` | Operation | 操作记录查询 |

### 1.2 接口清单

| # | 方法 | 路径 | 说明 | 状态 |
|---|------|------|------|------|
| 1 | `POST` | `/pools` | 创建池 | ✅ |
| 2 | `GET` | `/pools` | 池列表 | ✅ |
| 3 | `GET` | `/pools/{pool_id}` | 池详情（含成员） | ✅ |
| 4 | `PATCH` | `/pools/{pool_id}` | 更新池 | ✅ |
| 5 | `DELETE` | `/pools/{pool_id}` | 删除池 | ✅ |
| 6 | `POST` | `/pools/{pool_id}/members` | 批量添加成员 | ✅ |
| 7 | `DELETE` | `/pools/{pool_id}/members` | 批量删除成员 | ✅ |
| 8 | `GET` | `/pools/{pool_id}/members` | 成员列表 | ✅ |
| 9 | `PATCH` | `/pools/{pool_id}/members/{symbol}` | 更新成员备注 | ✅ |
| 10 | `DELETE` | `/pools/{pool_id}/members/{symbol}` | 删除单个成员 | ✅ |
| 11 | `GET` | `/pools/by-symbol/{symbol}` | 反向查询：股票在哪些池 | ✅ |
| 12 | `POST` | `/pools/{pool_id}/operations` | 发起池操作 | ✅ |
| 13 | `GET` | `/pools/{pool_id}/operations` | 操作历史 | ✅ |
| 14 | `GET` | `/operations/{op_id}` | 操作详情 | ✅ |
| 15 | `GET` | `/operations/{op_id}/progress` | 操作进度（轻量） | ✅ |
| 16 | `POST` | `/operations/{op_id}/cancel` | 取消操作 | ✅ |

---

## 2. 详细 API 规范

### 2.1 池管理

#### POST `/api/v1/pools` — 创建池

**请求**：
```json
{
  "name": "银行股组合",
  "pool_type": "industry",
  "description": "主要持仓的银行股",
  "color": "#52c41a",
  "icon": "🏦"
}
```

**响应**（201）：
```json
{
  "code": 201,
  "message": "创建成功",
  "data": {
    "id": 1,
    "name": "银行股组合",
    "pool_type": "industry",
    "description": "主要持仓的银行股",
    "color": "#52c41a",
    "icon": "🏦",
    "sort_order": 0,
    "is_default": false,
    "is_archived": false,
    "member_count": 0,
    "created_at": "2026-09-15T10:00:00",
    "updated_at": "2026-09-15T10:00:00"
  }
}
```

---

#### GET `/api/v1/pools` — 池列表

**Query 参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `include_archived` | bool | `false` | 是否包含已归档池 |
| `limit` | int | `100` | 每页数量 |
| `offset` | int | `0` | 偏移量 |

**响应**（200）：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 5,
    "items": [
      {
        "id": 1,
        "name": "我的自选",
        "pool_type": "watchlist",
        "icon": "⭐",
        "color": "#FFB800",
        "is_default": true,
        "member_count": 15,
        "created_at": "2026-09-15T10:00:00",
        "updated_at": "2026-09-15T12:00:00"
      },
      {
        "id": 2,
        "name": "银行股组合",
        "pool_type": "industry",
        "icon": "🏦",
        "color": "#52c41a",
        "is_default": false,
        "member_count": 8,
        "created_at": "2026-09-15T11:00:00",
        "updated_at": "2026-09-15T11:30:00"
      }
    ]
  }
}
```

---

#### GET `/api/v1/pools/{pool_id}` — 池详情

**响应**（200）：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "name": "银行股组合",
    "pool_type": "industry",
    "description": "主要持仓的银行股",
    "color": "#52c41a",
    "icon": "🏦",
    "sort_order": 0,
    "is_default": false,
    "is_archived": false,
    "member_count": 8,
    "created_at": "2026-09-15T10:00:00",
    "updated_at": "2026-09-15T12:00:00",
    "members": [
      {
        "symbol": "600000",
        "name": "浦发银行",
        "industry": "银行",
        "market": "主板",
        "exchange": "SSE",
        "memo": "核心持仓",
        "sort_order": 0,
        "added_at": "2026-09-15T10:30:00",
        "is_valid": true
      },
      {
        "symbol": "600016",
        "name": "民生银行",
        "industry": "银行",
        "market": "主板",
        "exchange": "SSE",
        "memo": "",
        "sort_order": 1,
        "added_at": "2026-09-15T10:35:00",
        "is_valid": true
      }
    ]
  }
}
```

**错误**（404）：
```json
{
  "code": 404,
  "message": "操作池不存在: 999",
  "data": null
}
```

---

#### PATCH `/api/v1/pools/{pool_id}` — 更新池

**请求**（部分更新）：
```json
{
  "name": "新版银行股组合",
  "color": "#1890ff"
}
```

**响应**（200）：
```json
{
  "code": 200,
  "message": "更新成功",
  "data": {
    "id": 1,
    "name": "新版银行股组合",
    "color": "#1890ff",
    ...
  }
}
```

---

#### DELETE `/api/v1/pools/{pool_id}` — 删除池

**响应**（200）：
```json
{
  "code": 200,
  "message": "删除成功",
  "data": null
}
```

**错误**（400，默认池不可删）：
```json
{
  "code": 400,
  "message": "无法删除默认池",
  "data": null
}
```

---

### 2.2 成员管理

#### POST `/api/v1/pools/{pool_id}/members` — 批量添加成员

**请求**：
```json
{
  "symbols": ["600000", "600016", "600036", "000001"],
  "validate_exists": true
}
```

**响应**（200）：
```json
{
  "code": 200,
  "message": "添加完成",
  "data": {
    "pool_id": 1,
    "added": ["600000", "600016", "600036"],
    "skipped": ["000001"],
    "total_added": 3,
    "total_skipped": 1
  }
}
```

---

#### DELETE `/api/v1/pools/{pool_id}/members` — 批量删除成员

**请求**：
```json
{
  "symbols": ["600000", "000001"]
}
```

**响应**（200）：
```json
{
  "code": 200,
  "message": "成功移除 2 个成员",
  "data": {
    "removed_count": 2
  }
}
```

---

#### GET `/api/v1/pools/{pool_id}/members` — 成员列表

**Query 参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `limit` | int | `100` | 每页数量 |
| `offset` | int | `0` | 偏移量 |

**响应**（200）：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "pool_id": 1,
    "total": 8,
    "items": [
      {
        "symbol": "600000",
        "name": "浦发银行",
        "industry": "银行",
        "market": "主板",
        "exchange": "SSE",
        "memo": "核心持仓",
        "sort_order": 0,
        "added_at": "2026-09-15T10:30:00",
        "is_valid": true
      }
    ]
  }
}
```

---

#### PATCH `/api/v1/pools/{pool_id}/members/{symbol}` — 更新成员备注

**请求**：
```json
{
  "memo": "长期持有"
}
```

**响应**（200）：
```json
{
  "code": 200,
  "message": "更新成功",
  "data": {
    "symbol": "600000",
    "memo": "长期持有",
    "is_valid": true
  }
}
```

---

#### DELETE `/api/v1/pools/{pool_id}/members/{symbol}` — 删除单个成员

**响应**（200）：
```json
{
  "code": 200,
  "message": "成员已移除",
  "data": null
}
```

---

### 2.3 反向查询

#### GET `/api/v1/pools/by-symbol/{symbol}` — 股票在哪些池

**响应**（200）：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "symbol": "600036",
    "pools": [
      {
        "id": 1,
        "name": "我的自选",
        "pool_type": "watchlist",
        "icon": "⭐",
        "color": "#FFB800",
        "is_default": true
      },
      {
        "id": 2,
        "name": "银行股组合",
        "pool_type": "industry",
        "icon": "🏦",
        "color": "#52c41a",
        "is_default": false
      }
    ],
    "total": 2
  }
}
```

---

### 2.4 池级操作

#### POST `/api/v1/pools/{pool_id}/operations` — 发起池操作

**请求**：
```json
{
  "operation_type": "kline_collect",
  "days": 365,
  "source": "akshare"
}
```

**响应**（201）：
```json
{
  "code": 201,
  "message": "操作已派发，共 8 只股票",
  "data": {
    "operation_id": 100,
    "pool_id": 1,
    "operation_type": "kline_collect",
    "status": "pending",
    "total": 8
  }
}
```

**错误**（409，操作冲突）：
```json
{
  "code": 409,
  "message": "池 1 已有进行中的操作，请等待完成后重试",
  "data": null
}
```

---

#### GET `/api/v1/pools/{pool_id}/operations` — 操作历史

**Query 参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `limit` | int | `20` | 每页数量 |
| `offset` | int | `0` | 偏移量 |

**响应**（200）：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "pool_id": 1,
    "total": 3,
    "items": [
      {
        "id": 100,
        "operation_type": "kline_collect",
        "status": "running",
        "params": {"days": 365, "source": "akshare"},
        "progress": {
          "done": 5,
          "total": 8,
          "failed": 0
        },
        "started_at": "2026-09-15T14:00:00",
        "created_at": "2026-09-15T14:00:00"
      },
      {
        "id": 99,
        "operation_type": "kline_collect",
        "status": "success",
        "params": {"days": 30, "source": "akshare"},
        "progress": {
          "done": 8,
          "total": 8,
          "failed": 0
        },
        "result_summary": {
          "total": 8,
          "saved": 2920,
          "skipped": 0,
          "failed": 0
        },
        "started_at": "2026-09-15T10:00:00",
        "finished_at": "2026-09-15T10:02:30",
        "created_at": "2026-09-15T10:00:00"
      }
    ]
  }
}
```

---

#### GET `/api/v1/operations/{op_id}` — 操作详情

**响应**（200）：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 100,
    "pool_id": 1,
    "operation_type": "kline_collect",
    "status": "success",
    "params": {"days": 365, "source": "akshare"},
    "progress": {"done": 8, "total": 8, "failed": 0},
    "result_summary": {
      "total": 8,
      "saved": 2920,
      "skipped": 0,
      "failed": 0,
      "details": [
        {"symbol": "600000", "status": "success", "count": 365},
        {"symbol": "600016", "status": "success", "count": 365},
        {"symbol": "600036", "status": "success", "count": 365},
        {"symbol": "000001", "status": "success", "count": 365},
        {"symbol": "000002", "status": "skipped", "message": "no data"},
        {"symbol": "000004", "status": "success", "count": 365},
        {"symbol": "000005", "status": "success", "count": 365},
        {"symbol": "000006", "status": "success", "count": 365}
      ]
    },
    "started_at": "2026-09-15T14:00:00",
    "finished_at": "2026-09-15T14:02:30",
    "created_at": "2026-09-15T14:00:00"
  }
}
```

---

#### GET `/api/v1/operations/{op_id}/progress` — 操作进度（轻量）

**响应**（200）：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "done": 5,
    "total": 8,
    "failed": 0
  }
}
```

**用途**：前端轮询 / SSE 断线重连时快速获取进度。

---

#### POST `/api/v1/operations/{op_id}/cancel` — 取消操作

**响应**（200）：
```json
{
  "code": 200,
  "message": "操作已取消",
  "data": {
    "id": 100,
    "status": "cancelled"
  }
}
```

---

## 3. 完整路由文件

```python
# route/api/v1/pool.py

from functools import lru_cache
from fastapi import APIRouter, Depends, Path, Query, Body, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.pool import (
    PoolCreateRequest,
    PoolUpdateRequest,
    PoolAddMembersRequest,
    PoolRemoveMembersRequest,
    PoolUpdateMemberMemoRequest,
)
from application.dto.pool_operation import (
    PoolKlineCollectRequest,
    PoolOperationListRequest,
)
from application.pool_service import StockPoolAppService
from application.pool_operation_service import PoolOperationAppService
from application.exceptions import ApplicationError
from infrastructure.database.connection import get_db
from route.schemas import response as R

router = APIRouter(prefix="/api/v1", tags=["操作池"])


# ── 依赖注入 ──────────────────────────────────────────────

def get_pool_service(db: AsyncSession = Depends(get_db)) -> StockPoolAppService:
    return StockPoolAppService(session=db)


def get_pool_op_service(
    db: AsyncSession = Depends(get_db),
) -> PoolOperationAppService:
    return PoolOperationAppService(session=db)


# ════════════════════════════════════════════════════════════════
# 池管理
# ════════════════════════════════════════════════════════════════

@router.post(
    "/pools",
    summary="创建池",
    status_code=status.HTTP_201_CREATED,
)
async def create_pool(
    request: PoolCreateRequest,
    service: StockPoolAppService = Depends(get_pool_service),
):
    pool = await service.create_pool(request)
    return R.created(pool.model_dump(), "创建成功")


@router.get(
    "/pools",
    summary="池列表",
)
async def list_pools(
    include_archived: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    service: StockPoolAppService = Depends(get_pool_service),
):
    result = await service.list_pools(
        include_archived=include_archived,
        limit=limit,
        offset=offset,
    )
    return R.ok(result.model_dump())


@router.get(
    "/pools/{pool_id}",
    summary="池详情（含成员）",
)
async def get_pool(
    pool_id: int = Path(..., description="池 ID"),
    service: StockPoolAppService = Depends(get_pool_service),
):
    pool = await service.get_pool(pool_id)
    return R.ok(pool.model_dump())


@router.patch(
    "/pools/{pool_id}",
    summary="更新池",
)
async def update_pool(
    pool_id: int = Path(...),
    request: PoolUpdateRequest = Body(...),
    service: StockPoolAppService = Depends(get_pool_service),
):
    pool = await service.update_pool(pool_id, request)
    return R.ok(pool.model_dump(), "更新成功")


@router.delete(
    "/pools/{pool_id}",
    summary="删除池",
)
async def delete_pool(
    pool_id: int = Path(...),
    service: StockPoolAppService = Depends(get_pool_service),
):
    await service.delete_pool(pool_id)
    return R.ok(message="删除成功")


# ════════════════════════════════════════════════════════════════
# 成员管理
# ════════════════════════════════════════════════════════════════

@router.post(
    "/pools/{pool_id}/members",
    summary="批量添加成员",
)
async def add_members(
    pool_id: int = Path(...),
    request: PoolAddMembersRequest = Body(...),
    service: StockPoolAppService = Depends(get_pool_service),
):
    result = await service.add_members(pool_id, request)
    return R.ok(result.model_dump(), "添加完成")


@router.delete(
    "/pools/{pool_id}/members",
    summary="批量删除成员",
)
async def remove_members(
    pool_id: int = Path(...),
    request: PoolRemoveMembersRequest = Body(...),
    service: StockPoolAppService = Depends(get_pool_service),
):
    count = await service.remove_members(pool_id, request)
    return R.ok({"removed_count": count}, f"成功移除 {count} 个成员")


@router.get(
    "/pools/{pool_id}/members",
    summary="成员列表",
)
async def list_members(
    pool_id: int = Path(...),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    service: StockPoolAppService = Depends(get_pool_service),
):
    result = await service.list_members(pool_id, limit, offset)
    return R.ok(result.model_dump())


@router.patch(
    "/pools/{pool_id}/members/{symbol}",
    summary="更新成员备注",
)
async def update_member_memo(
    pool_id: int = Path(...),
    symbol: str = Path(..., description="股票代码"),
    request: PoolUpdateMemberMemoRequest = Body(...),
    service: StockPoolAppService = Depends(get_pool_service),
):
    member = await service.update_member_memo(pool_id, request)
    return R.ok(member.model_dump(), "更新成功")


@router.delete(
    "/pools/{pool_id}/members/{symbol}",
    summary="删除单个成员",
)
async def remove_member(
    pool_id: int = Path(...),
    symbol: str = Path(...),
    service: StockPoolAppService = Depends(get_pool_service),
):
    await service.remove_members(
        pool_id, PoolRemoveMembersRequest(symbols=[symbol])
    )
    return R.ok(message="成员已移除")


# ════════════════════════════════════════════════════════════════
# 反向查询
# ════════════════════════════════════════════════════════════════

@router.get(
    "/pools/by-symbol/{symbol}",
    summary="股票在哪些池",
)
async def find_pools_by_symbol(
    symbol: str = Path(..., description="股票代码"),
    service: StockPoolAppService = Depends(get_pool_service),
):
    result = await service.find_pools_by_symbol(symbol)
    return R.ok(result.model_dump())


# ════════════════════════════════════════════════════════════════
# 池级操作
# ════════════════════════════════════════════════════════════════

@router.post(
    "/pools/{pool_id}/operations",
    summary="发起池操作",
    status_code=status.HTTP_201_CREATED,
)
async def create_pool_operation(
    pool_id: int = Path(...),
    request: PoolKlineCollectRequest = Body(...),
    service: PoolOperationAppService = Depends(get_pool_op_service),
):
    result = await service.create_kline_collect_operation(request)
    return R.created(result.model_dump(), result.message)


@router.get(
    "/pools/{pool_id}/operations",
    summary="操作历史",
)
async def list_pool_operations(
    pool_id: int = Path(...),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: PoolOperationAppService = Depends(get_pool_op_service),
):
    result = await service.list_operations(
        PoolOperationListRequest(pool_id=pool_id, limit=limit, offset=offset)
    )
    return R.ok(result.model_dump())


# ════════════════════════════════════════════════════════════════
# 操作记录
# ════════════════════════════════════════════════════════════════

@router.get(
    "/operations/{op_id}",
    summary="操作详情",
)
async def get_operation(
    op_id: int = Path(...),
    service: PoolOperationAppService = Depends(get_pool_op_service),
):
    op = await service.get_operation(op_id)
    return R.ok(op.model_dump())


@router.get(
    "/operations/{op_id}/progress",
    summary="操作进度（轻量）",
)
async def get_operation_progress(
    op_id: int = Path(...),
    service: PoolOperationAppService = Depends(get_pool_op_service),
):
    progress = await service.get_operation_progress(op_id)
    return R.ok(progress.model_dump())


@router.post(
    "/operations/{op_id}/cancel",
    summary="取消操作",
)
async def cancel_operation(
    op_id: int = Path(...),
    service: PoolOperationAppService = Depends(get_pool_op_service),
):
    op = await service.cancel_operation(op_id)
    return R.ok(op.model_dump(), "操作已取消")
```

---

## 4. 路由注册

在 `main.py` 或 `route/api/router.py` 中注册：

```python
# route/api/router.py

from route.api.v1.pool import router as pool_router

api_router = APIRouter(prefix="/api")
api_router.include_router(pool_router)
```

---

## 5. 全局异常处理

在 `main.py` 的全局异常处理中捕获 `ApplicationError`：

```python
from application.exceptions import ApplicationError

@app.exception_handler(ApplicationError)
async def application_error_handler(request: Request, exc: ApplicationError):
    return JSONResponse(
        status_code=exc.code or 500,
        content={"code": exc.code or 500, "message": exc.message, "data": None},
    )
```

---

## 6. API 兼容性说明

| 决策 | 说明 |
|------|------|
| v1 API 路径 | `/api/v1/pools/*` |
| 未来 v2 路径 | `/api/v2/pools/*`（在路由层决定） |
| 响应格式 | `{code, message, data}` 保持不变 |
| 分页 | 基于 `limit` / `offset`（非 cursor） |

---

## 7. 性能考量

| 接口 | 性能要求 | 优化 |
|------|---------|------|
| `GET /pools` | < 50ms | 不加载成员 |
| `GET /pools/{pool_id}` | < 200ms | `selectinload` 成员 |
| `POST /pools/{id}/members` | < 500ms | 批量插入 |
| `POST /pools/{id}/operations` | < 200ms | 派发后台任务后立即返回 |
| `GET /operations/{id}/progress` | < 30ms | 轻量查询 |
