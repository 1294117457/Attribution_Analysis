# 06 - router + app 入口层

> **router.py**：各业务域的路由，只做三件事——接收 DTO、调 Service、返回 VO。零 try/except。
> **app/main.py**：FastAPI 入口，注册路由、中间件、异常处理器、数据库初始化。

---

## kline/router.py

```python
"""K线路由

职责：接收请求 → 调 Service → 返回响应
规范：
    - 零 try/except（异常由全局 handler 处理）
    - 使用 R.ok() 统一包装响应
    - Depends(get_db) 注入 AsyncSession
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from infra.database.connection import get_db
from kline.service import KlineService
from kline.schema import (
    KlineCollectRequest,
    KlineVO,
    KlineListVO,
    KlineCollectVO,
)
from app import response as R

router = APIRouter(prefix="/api/klines", tags=["K线"])


@router.get("/{symbol}", summary="查询K线数据")
async def get_klines(
    symbol: str,
    start_date: Optional[date] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[date] = Query(None, description="结束日期 YYYY-MM-DD"),
    limit: int = Query(365, ge=1, le=3650, description="最大返回条数"),
    order_asc: bool = Query(True, description="是否按日期升序（ECharts 需要升序）"),
    db: AsyncSession = Depends(get_db),
):
    klines = await KlineService.get_klines(db, symbol, start_date, end_date, limit, order_asc)
    items = [KlineVO.model_validate(k) for k in klines]
    return R.ok(KlineListVO(total=len(items), items=items).model_dump())


@router.post("/collect", summary="采集K线数据", status_code=201)
async def collect_kline(
    req: KlineCollectRequest,
    db: AsyncSession = Depends(get_db),
):
    vo = await KlineService.collect_and_save(
        db,
        symbol=req.symbol,
        days=req.days,
        start_date=req.start_date,
        end_date=req.end_date,
    )
    return R.ok(vo.model_dump())


@router.delete("/{symbol}", summary="删除股票全部K线")
async def delete_klines(symbol: str, db: AsyncSession = Depends(get_db)):
    deleted = await KlineService.delete_by_symbol(db, symbol)
    return R.ok({"deleted_count": deleted})


@router.delete("/{symbol}/{trade_date}", summary="删除单条K线")
async def delete_one_kline(
    symbol: str,
    trade_date: date,
    db: AsyncSession = Depends(get_db),
):
    deleted = await KlineService.delete_one(db, symbol, trade_date)
    return R.ok({"deleted_count": deleted})
```

---

## stock_info/router.py

```python
"""股票信息路由"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from infra.database.connection import get_db
from stock_info.service import StockInfoService
from stock_info.schema import StockInfoVO, StockListVO
from app import response as R

router = APIRouter(prefix="/api/stocks", tags=["股票"])


@router.get("/", summary="股票列表（含K线统计）")
async def list_stocks(db: AsyncSession = Depends(get_db)):
    vo = await StockInfoService.list_stocks(db)
    return R.ok(vo.model_dump())


@router.get("/{symbol}", summary="股票详情")
async def get_stock(symbol: str, db: AsyncSession = Depends(get_db)):
    info = await StockInfoService.get(db, symbol)
    if info is None:
        raise HTTPException(status_code=404, detail=f"股票 {symbol} 不存在")
    return R.ok(StockInfoVO.model_validate(info).model_dump())
```

---

## indicators/router.py

```python
"""技术指标路由"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from infra.database.connection import get_db
from indicators.service import IndicatorService
from app import response as R

router = APIRouter(prefix="/api/indicators", tags=["技术指标"])


@router.get("/{symbol}", summary="获取技术指标（MA/MACD/RSI）")
async def get_indicators(
    symbol: str,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    vo = await IndicatorService.get_indicators(db, symbol, start_date, end_date)
    return R.ok(vo.model_dump())
```

---

## app/main.py

```python
"""FastAPI 应用入口"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from infra.config import get_settings
from infra.database.base import Base
from infra.database.connection import async_engine, close_db

# 注册所有 model（确保 metadata 建表时能发现）
import kline.model        # noqa: F401
import stock_info.model   # noqa: F401

# 导入路由
from kline.router import router as kline_router
from stock_info.router import router as stock_info_router
from indicators.router import router as indicators_router
from app.handlers import register_exception_handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)

settings = get_settings()

ROUTERS = [
    kline_router,        # /api/klines
    stock_info_router,   # /api/stocks
    indicators_router,   # /api/indicators
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：建表
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # 关闭：释放连接池
    await close_db()


def create_app() -> FastAPI:
    app = FastAPI(
        title="智能金融数据归因分析平台",
        description="数据采集 + 技术指标 + 异常检测 + 归因分析",
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

    # 全局异常处理
    register_exception_handlers(app)

    # 注册路由
    for router in ROUTERS:
        app.include_router(router)

    return app


app = create_app()


@app.get("/health", tags=["系统"])
async def health():
    return {"status": "ok", "version": "2.0.0"}
```

---

## app/handlers/__init__.py（全局异常处理）

```python
"""全局异常处理器"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=400,
            content={"code": 400, "message": str(exc), "data": None},
        )

    @app.exception_handler(RuntimeError)
    async def runtime_error_handler(request: Request, exc: RuntimeError):
        return JSONResponse(
            status_code=502,
            content={"code": 502, "message": str(exc), "data": None},
        )

    @app.exception_handler(Exception)
    async def generic_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": "服务器内部错误", "data": None},
        )
```

---

## app/dependencies.py

```python
"""FastAPI 依赖注入导出"""

from infra.database.connection import get_db

__all__ = ["get_db"]
```

---

## API 端点汇总

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/api/stocks/` | 股票列表 + K线统计 |
| GET | `/api/stocks/{symbol}` | 股票详情 |
| POST | `/api/klines/collect` | 采集K线 |
| GET | `/api/klines/{symbol}` | 查询K线 |
| DELETE | `/api/klines/{symbol}` | 删除股票全部K线 |
| DELETE | `/api/klines/{symbol}/{trade_date}` | 删除单条K线 |
| GET | `/api/indicators/{symbol}` | 技术指标（MA/MACD/RSI） |

---

## 注意事项

1. **路由零 try/except**：任何业务异常（ValueError/RuntimeError）由全局 handler 处理，路由只做正常流程
2. **路由 prefix 不加 `/api/v1`**：router 内部已含 `/api/xxx`，main.py 直接 `include_router` 不加额外 prefix
3. **`import kline.model` 必须在 lifespan 之前执行**：否则 `Base.metadata.create_all` 找不到这些表
4. **`model_validate` vs `model_dump`**：
   - ORM → VO：`KlineVO.model_validate(orm_obj)`
   - VO → dict（返回给前端）：`vo.model_dump()`
5. **`status_code=201`**：POST 采集接口返回 201 Created，符合 REST 规范
