# 04 - Route 路由层

> 路由层负责接收 HTTP 请求、参数校验、调用应用服务、返回 HTTP 响应。
> 路由层**不包含业务逻辑**，只做请求/响应的格式转换（DTO ↔ DTO）。

---

## 目录结构

```
src/route/
├── __init__.py
├── api/
│   ├── __init__.py
│   ├── v1/
│   │   ├── __init__.py
│   │   ├── kline.py              # K线路由
│   │   └── stock.py              # 股票路由
│   └── router.py                 # 路由聚合
├── schemas/
│   ├── __init__.py
│   ├── request.py                # 请求 DTO（可选，复杂请求可独立）
│   └── response.py               # 统一响应格式
└── dependencies.py               # 路由层依赖注入
```

---

## 与上下游的关系

```
┌──────────────────────────┐
│      Client (HTTP)       │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐         ┌──────────────────────────┐
│       Route Layer        │ ──────▶ │     Application Layer     │
│  路由层职责：             │         │  应用层职责：               │
│  - 接收 HTTP 请求         │         │  - 用例编排                │
│  - 参数校验（Pydantic）   │         │  - 事务边界                │
│  - 转换为 DTO             │         │  - 调用领域/基础设施        │
│  - 调用 AppService        │         │                           │
│  - 返回 JSON 响应         │         │                           │
└──────────────────────────┘         └──────────────────────────┘
```

**路由层禁止做的事**：
- 包含业务逻辑（业务规则在领域层）
- 直接操作数据库（数据库访问在仓储层）
- 调用外部 API（API 调用在防腐层）
- 异常处理（异常处理在全局 handler）

---

## route/schemas/response.py 统一响应

```python
"""统一 API 响应格式

所有 API 统一用此格式包装，前端按 code 判断成功/失败。
"""

from typing import Any, Optional
from fastapi.responses import JSONResponse


def ok(data: Any = None, message: str = "success") -> dict:
    """成功响应
    
    FastAPI 会自动将 dict 序列化为 JSON。
    返回 200 状态码。
    
    用法：
        return ok({"id": 1})
        return ok(items, message="查询成功")
    """
    return {"code": 200, "message": message, "data": data}


def created(data: Any = None, message: str = "创建成功") -> dict:
    """创建成功响应
    
    用于 POST 请求成功创建资源。
    返回 201 状态码。
    
    用法：
        return created({"id": 1})
    """
    return {"code": 201, "message": message, "data": data}


def no_content(message: str = "操作成功") -> dict:
    """无内容响应
    
    用于 DELETE 等不返回具体数据的操作。
    返回 200 状态码。
    """
    return {"code": 200, "message": message, "data": None}


def err(message: str, code: int = 400) -> JSONResponse:
    """错误响应
    
    返回非 200 状态码，响应体包含错误信息。
    
    用法：
        return err("参数错误", 400)
        return err("资源不存在", 404)
    """
    return JSONResponse(
        status_code=code,
        content={"code": code, "message": message, "data": None},
    )


# 常用错误快捷方法
def bad_request(message: str) -> JSONResponse:
    """400 错误 - 请求参数错误"""
    return err(message, 400)


def not_found(message: str) -> JSONResponse:
    """404 错误 - 资源不存在"""
    return err(message, 404)


def conflict(message: str) -> JSONResponse:
    """409 错误 - 资源冲突"""
    return err(message, 409)


def server_error(message: str = "服务器内部错误") -> JSONResponse:
    """500 错误 - 服务器内部错误"""
    return err(message, 500)


def gateway_error(message: str) -> JSONResponse:
    """502 错误 - 网关错误（通常用于外部服务调用失败）"""
    return err(message, 502)
```

---

## route/api/v1/kline.py K线路由

```python
"""K线 API 路由

职责：
1. 接收 HTTP 请求参数
2. 转换为应用层 DTO
3. 调用应用服务
4. 返回标准化响应

禁止：
- 禁止包含业务逻辑
- 禁止直接操作数据库
- 禁止捕获异常（由全局 handler 处理）
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.kline_service import KlineAppService
from application.dto.kline import (
    KlineCollectRequest,
    KlineQueryRequest,
    KlineDeleteRequest,
)
from infrastructure.database.connection import get_db
from infrastructure.collectors.akshare import AkShareFetcher
from domain.kline.schemas import KlineBO

from route.schemas import response as R

router = APIRouter(prefix="/klines", tags=["K线"])


# ════════════════════════════════════════════════════════════════
# 依赖注入工厂
# ════════════════════════════════════════════════════════════════

def get_kline_service(
    db: AsyncSession = Depends(get_db),
) -> KlineAppService:
    """创建 K线应用服务"""
    return KlineAppService(session=db)


def get_kline_fetcher() -> AkShareFetcher:
    """创建 AkShare 采集器（单例）"""
    return AkShareFetcher(KlineBO)


# ════════════════════════════════════════════════════════════════
# 查询路由
# ════════════════════════════════════════════════════════════════

@router.get("/{symbol}", summary="查询K线")
async def get_klines(
    symbol: str,
    start_date: Optional[date] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[date] = Query(None, description="结束日期 YYYY-MM-DD"),
    limit: int = Query(365, ge=1, le=3650, description="最大返回条数"),
    order_desc: bool = Query(True, description="是否按日期降序"),
    service: KlineAppService = Depends(get_kline_service),
):
    """查询股票的K线数据
    
    默认按日期降序返回，最新的K线在前面。
    """
    request = KlineQueryRequest(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        order_desc=order_desc,
    )
    response = await service.get_klines(request)
    return R.ok(response.model_dump())


@router.get("/{symbol}/stats", summary="K线统计")
async def get_kline_stats(
    symbol: str,
    service: KlineAppService = Depends(get_kline_service),
):
    """获取K线统计信息（条数、日期范围、最新收盘价等）"""
    stats = await service.get_stats(symbol)
    return R.ok(stats.model_dump())


@router.get("/{symbol}/{trade_date}", summary="查询单条K线")
async def get_kline_by_date(
    symbol: str,
    trade_date: date,
    service: KlineAppService = Depends(get_kline_service),
):
    """根据日期查询单条K线"""
    kline = await service.get_kline_by_date(symbol, trade_date)
    return R.ok(kline.model_dump())


# ════════════════════════════════════════════════════════════════
# 采集路由
# ════════════════════════════════════════════════════════════════

@router.post(
    "/collect",
    summary="采集K线",
    status_code=status.HTTP_201_CREATED,
)
async def collect_kline(
    request: KlineCollectRequest,
    service: KlineAppService = Depends(get_kline_service),
    fetcher: AkShareFetcher = Depends(get_kline_fetcher),
):
    """采集并存储K线数据
    
    从外部数据源（默认 AkShare）获取指定股票的历史K线数据。
    """
    response = await service.collect(request, fetcher)
    return R.created(response.model_dump())


@router.post(
    "/collect/batch",
    summary="批量采集K线",
    status_code=status.HTTP_201_CREATED,
)
async def collect_batch(
    symbols: list[str] = Query(..., description="股票代码列表"),
    days: int = Query(30, ge=1, le=3650, description="回溯天数"),
    service: KlineAppService = Depends(get_kline_service),
    fetcher: AkShareFetcher = Depends(get_kline_fetcher),
):
    """批量采集多只股票的K线数据
    
    单只失败不影响其他股票，失败信息会记录在对应 symbol 的 message 中。
    """
    results = await service.collect_batch(symbols, days, fetcher)
    return R.created({
        symbol: resp.model_dump()
        for symbol, resp in results.items()
    })


# ════════════════════════════════════════════════════════════════
# 删除路由
# ════════════════════════════════════════════════════════════════

@router.delete("/{symbol}", summary="删除全部K线")
async def delete_all_klines(
    symbol: str,
    service: KlineAppService = Depends(get_kline_service),
):
    """删除指定股票的所有K线数据"""
    request = KlineDeleteRequest(symbol=symbol)
    response = await service.delete(request)
    return R.no_content() if response.deleted_count == 0 else R.ok(response.model_dump())


@router.delete("/{symbol}/{trade_date}", summary="删除单条K线")
async def delete_kline(
    symbol: str,
    trade_date: date,
    service: KlineAppService = Depends(get_kline_service),
):
    """删除指定日期的K线数据"""
    request = KlineDeleteRequest(symbol=symbol, trade_date=trade_date)
    response = await service.delete(request)
    return R.no_content() if response.deleted_count == 0 else R.ok(response.model_dump())
```

---

## route/api/v1/stock.py 股票路由

```python
"""股票 API 路由

职责：接收 HTTP 请求、参数校验、调用应用服务、返回标准化响应。
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.stock_service import StockAppService
from application.dto.stock import StockUpdateRequest
from infrastructure.database.connection import get_db

from route.schemas import response as R

router = APIRouter(prefix="/stocks", tags=["股票"])


def get_stock_service(
    db: AsyncSession = Depends(get_db),
) -> StockAppService:
    """创建股票应用服务"""
    return StockAppService(session=db)


# ════════════════════════════════════════════════════════════════
# 查询路由
# ════════════════════════════════════════════════════════════════

@router.get("/", summary="股票列表")
async def list_stocks(
    industry: Optional[str] = Query(None, description="按行业筛选"),
    market: Optional[str] = Query(None, description="按市场筛选（SH/SZ/BSE）"),
    service: StockAppService = Depends(get_stock_service),
):
    """获取所有已采集的股票列表（含K线统计）"""
    response = await service.list_stocks(industry=industry, market=market)
    return R.ok(response.model_dump())


@router.get("/{symbol}", summary="股票详情")
async def get_stock(
    symbol: str,
    service: StockAppService = Depends(get_stock_service),
):
    """获取股票详细信息"""
    stock = await service.get_stock(symbol)
    return R.ok(stock.model_dump())


# ════════════════════════════════════════════════════════════════
# 写入路由
# ════════════════════════════════════════════════════════════════

@router.post(
    "/",
    summary="新增/更新股票",
    status_code=status.HTTP_201_CREATED,
)
async def upsert_stock(
    symbol: str = Query(..., description="股票代码"),
    name: str = Query(..., description="股票名称"),
    industry: Optional[str] = Query(None, description="所属行业"),
    market: Optional[str] = Query(None, description="所属市场"),
    service: StockAppService = Depends(get_stock_service),
):
    """新增或更新股票信息（基于 symbol 去重）"""
    stock = await service.upsert_stock(symbol, name, industry, market)
    return R.created(stock.model_dump())


@router.patch("/{symbol}", summary="部分更新股票")
async def update_stock(
    symbol: str,
    request: StockUpdateRequest,
    service: StockAppService = Depends(get_stock_service),
):
    """部分更新股票信息（只更新提供的字段）"""
    stock = await service.update_stock(symbol, request)
    return R.ok(stock.model_dump())


# ════════════════════════════════════════════════════════════════
# 删除路由
# ════════════════════════════════════════════════════════════════

@router.delete("/{symbol}", summary="删除股票")
async def delete_stock(
    symbol: str,
    service: StockAppService = Depends(get_stock_service),
):
    """删除股票及其所有K线数据"""
    response = await service.delete_stock(symbol)
    return R.ok(response.model_dump())
```

---

## route/api/router.py 路由聚合

```python
"""API 路由聚合

将各业务域的路由聚合到一个总路由下。
通常会加上 API 版本前缀（如 /api/v1）。
"""

from fastapi import APIRouter

from route.api.v1.kline import router as kline_router
from route.api.v1.stock import router as stock_router

# API v1 路由
api_router = APIRouter(prefix="/api/v1")

api_router.include_router(kline_router)
api_router.include_router(stock_router)
```

---

## route/dependencies.py 依赖注入

```python
"""路由层依赖注入

定义 FastAPI Depends 依赖项。
依赖工厂负责创建服务实例、注入必需的依赖。
"""

from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.connection import get_db
from application.kline_service import KlineAppService
from application.stock_service import StockAppService
from infrastructure.collectors.akshare import AkShareFetcher
from domain.kline.schemas import KlineBO

__all__ = [
    "get_db",
    "get_kline_service",
    "get_stock_service",
    "get_kline_fetcher",
]


def get_kline_service(db: AsyncSession = Depends(get_db)) -> KlineAppService:
    """K线应用服务依赖"""
    return KlineAppService(session=db)


def get_stock_service(db: AsyncSession = Depends(get_db)) -> StockAppService:
    """股票应用服务依赖"""
    return StockAppService(session=db)


@lru_cache
def get_kline_fetcher() -> AkShareFetcher:
    """K线采集器依赖（单例）
    
    采集器是无状态的，可以作为单例复用。
    """
    return AkShareFetcher(KlineBO)
```

---

## main.py 应用入口

```python
"""FastAPI 应用入口"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from infrastructure.config import get_settings
from infrastructure.database.base import Base
from infrastructure.database.connection import async_engine, close_db

# 导入所有 ORM 模型（用于表创建）
from infrastructure.database.models.kline import DailyKlineDB          # noqa: F401
from infrastructure.database.models.stock_info import StockInfoDB      # noqa: F401

# 导入路由
from route.api.router import api_router

# 导入应用层异常（用于全局异常处理）
from application.exceptions import (
    ApplicationError,
    KlineNotFoundError,
    StockNotFoundError,
    KlineDataError,
    CollectionError,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """应用生命周期管理
    
    启动时创建所有表，关闭时释放连接池。
    """
    # 启动：创建所有表
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # 关闭：释放连接池
    await close_db()


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title="智能金融数据归因分析平台",
        description="DDD 架构 - 数据采集 + 技术指标 + 异常检测 + 归因分析",
        version="2.0.0",
        lifespan=lifespan,
    )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册全局异常处理器
    register_exception_handlers(app)
    
    # 注册路由
    app.include_router(api_router)
    
    return app


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器
    
    所有应用层异常都转换为统一的 JSON 响应格式：
    { "code": xxx, "message": "xxx", "data": null }
    """
    
    @app.exception_handler(KlineNotFoundError)
    async def kline_not_found(request: Request, exc: KlineNotFoundError):
        return JSONResponse(
            status_code=404,
            content={"code": 404, "message": exc.message, "data": None},
        )
    
    @app.exception_handler(StockNotFoundError)
    async def stock_not_found(request: Request, exc: StockNotFoundError):
        return JSONResponse(
            status_code=404,
            content={"code": 404, "message": exc.message, "data": None},
        )
    
    @app.exception_handler(KlineDataError)
    async def kline_data_error(request: Request, exc: KlineDataError):
        return JSONResponse(
            status_code=400,
            content={"code": 400, "message": exc.message, "data": None},
        )
    
    @app.exception_handler(CollectionError)
    async def collection_error(request: Request, exc: CollectionError):
        return JSONResponse(
            status_code=502,
            content={"code": 502, "message": exc.message, "data": None},
        )
    
    @app.exception_handler(ApplicationError)
    async def application_error(request: Request, exc: ApplicationError):
        return JSONResponse(
            status_code=400,
            content={"code": 400, "message": exc.message, "data": None},
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        """Pydantic 校验失败"""
        return JSONResponse(
            status_code=422,
            content={
                "code": 422,
                "message": "请求参数校验失败",
                "data": {"errors": exc.errors()},
            },
        )
    
    @app.exception_handler(ValueError)
    async def value_error(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=400,
            content={"code": 400, "message": str(exc), "data": None},
        )
    
    @app.exception_handler(RuntimeError)
    async def runtime_error(request: Request, exc: RuntimeError):
        return JSONResponse(
            status_code=502,
            content={"code": 502, "message": str(exc), "data": None},
        )
    
    @app.exception_handler(Exception)
    async def generic_error(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": "服务器内部错误", "data": None},
        )


app = create_app()


@app.get("/health", tags=["系统"])
async def health():
    """健康检查"""
    return {"status": "ok", "version": "2.0.0"}
```

---

## dependencies.py 顶级依赖导出

```python
"""项目级依赖导出

业务代码可从这里直接 import 常用依赖。
"""

from infrastructure.database.connection import get_db

__all__ = ["get_db"]
```

---

## API 端点汇总

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/api/v1/stocks/` | 股票列表（支持 industry、market 筛选） |
| GET | `/api/v1/stocks/{symbol}` | 股票详情 |
| POST | `/api/v1/stocks/` | 新增/更新股票 |
| PATCH | `/api/v1/stocks/{symbol}` | 部分更新股票 |
| DELETE | `/api/v1/stocks/{symbol}` | 删除股票 |
| GET | `/api/v1/klines/{symbol}` | 查询K线（按日期范围） |
| GET | `/api/v1/klines/{symbol}/stats` | K线统计 |
| GET | `/api/v1/klines/{symbol}/{date}` | 查询单条K线 |
| POST | `/api/v1/klines/collect` | 采集K线 |
| POST | `/api/v1/klines/collect/batch` | 批量采集K线 |
| DELETE | `/api/v1/klines/{symbol}` | 删除全部K线 |
| DELETE | `/api/v1/klines/{symbol}/{date}` | 删除单条K线 |

---

## 请求示例

### 采集K线

```bash
curl -X POST "http://localhost:8000/api/v1/klines/collect" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "000001",
    "days": 365,
    "start_date": "2024-01-01",
    "end_date": "2024-12-31"
  }'
```

**响应**：

```json
{
  "code": 201,
  "message": "成功采集 250 条新数据（共获取 250 条）",
  "data": {
    "symbol": "000001",
    "name": "平安银行",
    "saved_count": 250,
    "total_count": 250,
    "message": "成功采集 250 条新数据（共获取 250 条）"
  }
}
```

### 查询K线

```bash
curl -X GET "http://localhost:8000/api/v1/klines/000001?start_date=2024-01-01&end_date=2024-12-31&limit=100"
```

**响应**：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 100,
    "items": [
      {
        "symbol": "000001",
        "name": "平安银行",
        "date": "2024-01-02",
        "open": 9.25,
        "high": 9.30,
        "low": 9.20,
        "close": 9.28,
        "volume": 1234567,
        "amount": 114567890.0,
        "change_pct": 0.32
      }
    ]
  }
}
```

---

## 注意事项

1. **路由零 try/except**：所有业务异常由全局 exception handler 处理
2. **依赖注入创建服务**：使用 `Depends()` 工厂函数创建服务实例，便于测试
3. **参数校验在 DTO 层**：使用 Pydantic 的 `Field` 定义校验规则
4. **响应格式统一**：所有响应使用 `R.ok()`、`R.created()`、`R.no_content()` 统一包装
5. **错误响应**：使用 `err()` 或快捷方法（`bad_request`、`not_found` 等）
6. **HTTP 状态码**：
   - 200：查询/更新成功
   - 201：创建资源成功
   - 204：无内容（DELETE 等）
   - 400：请求参数错误
   - 404：资源不存在
   - 409：资源冲突
   - 422：参数校验失败
   - 500：服务器内部错误
   - 502：网关错误（外部服务调用失败）
7. **路由参数顺序**：FastAPI 按定义顺序匹配路由，建议把更具体的路由放在前面
8. **不暴露内部异常**：路由层不要把异常详情暴露给客户端，统一使用友好提示
