# 03 - Application 应用层

> 应用层负责用例编排，调用领域服务和基础设施服务（仓储、采集器）。
> 应用层**不包含业务逻辑**，只负责业务流程的编排和协调。
> 上游：路由层（Route Layer）；下游：领域层、基础设施层。

---

## 目录结构

```
src/application/
├── __init__.py
├── dto/                          # 应用层 DTO
│   ├── __init__.py
│   ├── kline.py                  # K线相关 DTO
│   └── stock.py                  # 股票相关 DTO
├── kline_service.py              # K线应用服务
├── stock_service.py              # 股票应用服务
└── exceptions.py                 # 应用层异常
```

---

## application/dto/ 应用层 DTO

### dto/kline.py

```python
"""K线应用层 DTO

DTO（Data Transfer Object）是应用层与路由层之间的数据传输对象。
与领域层 VO 的区别：
- DTO 主要用于 API 请求/响应
- VO 用于领域层内部数据传输
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════
# 请求 DTO（API 请求 → 应用服务）
# ═══════════════════════════════════════════════════════════════════

class KlineCollectRequest(BaseModel):
    """采集K线请求"""
    
    symbol: str = Field(..., description="股票代码", examples=["000001"])
    days: int = Field(365, ge=1, le=3650, description="回溯天数")
    start_date: Optional[date] = Field(None, description="开始日期（优先于 days）")
    end_date: Optional[date] = Field(None, description="结束日期（默认今天）")


class KlineQueryRequest(BaseModel):
    """查询K线请求"""
    
    symbol: str = Field(..., description="股票代码")
    start_date: Optional[date] = Field(None, description="开始日期")
    end_date: Optional[date] = Field(None, description="结束日期")
    limit: int = Field(365, ge=1, le=3650, description="最大返回条数")
    order_desc: bool = Field(True, description="是否按日期降序")


class KlineDeleteRequest(BaseModel):
    """删除K线请求"""
    
    symbol: str = Field(..., description="股票代码")
    trade_date: Optional[date] = Field(None, description="交易日期（不传则删除全部）")


# ═══════════════════════════════════════════════════════════════════
# 响应 DTO（应用服务 → API 响应）
# ═══════════════════════════════════════════════════════════════════

class KlineItemResponse(BaseModel):
    """单条K线响应"""
    
    symbol: str
    name: str
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float
    change_pct: Optional[float] = None


class KlineListResponse(BaseModel):
    """K线列表响应"""
    
    total: int
    items: list[KlineItemResponse]


class KlineCollectResponse(BaseModel):
    """K线采集响应"""
    
    symbol: str
    name: str
    saved_count: int
    total_count: int
    message: str


class KlineDeleteResponse(BaseModel):
    """K线删除响应"""
    
    symbol: str
    deleted_count: int
    message: str


class KlineStatsResponse(BaseModel):
    """K线统计响应"""
    
    symbol: str
    name: str
    count: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    latest_close: Optional[float] = None
    latest_volume: Optional[int] = None
```

### dto/stock.py

```python
"""股票应用层 DTO"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════
# 请求 DTO
# ═══════════════════════════════════════════════════════════════════

class StockUpdateRequest(BaseModel):
    """更新股票信息请求"""
    
    name: Optional[str] = Field(None, description="股票名称")
    industry: Optional[str] = Field(None, description="所属行业")
    market: Optional[str] = Field(None, description="所属市场")


# ═══════════════════════════════════════════════════════════════════
# 响应 DTO
# ═══════════════════════════════════════════════════════════════════

class StockItemResponse(BaseModel):
    """股票详情响应"""
    
    symbol: str
    name: Optional[str] = None
    industry: Optional[str] = None
    market: Optional[str] = None
    list_date: Optional[date] = None
    total_shares: Optional[int] = None


class StockListItemResponse(BaseModel):
    """股票列表项（含K线统计）"""
    
    symbol: str
    name: Optional[str] = None
    industry: Optional[str] = None
    market: Optional[str] = None
    record_count: int = 0
    kline_start: Optional[date] = None
    kline_end: Optional[date] = None


class StockListResponse(BaseModel):
    """股票列表响应"""
    
    total: int
    items: list[StockListItemResponse]


class StockDeleteResponse(BaseModel):
    """删除股票响应"""
    
    symbol: str
    deleted_count: int
    message: str
```

---

## application/exceptions.py 应用层异常

```python
"""应用层异常

应用层异常是业务层面的错误，不涉及技术细节。
与基础设施层异常（数据库连接失败等）区分。
"""

from domain.kline.value_objects import StockCode


class ApplicationError(Exception):
    """应用层异常基类"""
    
    def __init__(self, message: str, code: str = "APP_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class KlineNotFoundError(ApplicationError):
    """K线不存在"""
    
    def __init__(self, symbol: str, date: str = None):
        if date:
            msg = f"股票 {symbol} 在 {date} 的K线不存在"
        else:
            msg = f"股票 {symbol} 的K线不存在"
        super().__init__(msg, "KLINE_NOT_FOUND")
        self.symbol = symbol


class StockNotFoundError(ApplicationError):
    """股票不存在"""
    
    def __init__(self, symbol: str):
        super().__init__(f"股票 {symbol} 不存在", "STOCK_NOT_FOUND")
        self.symbol = symbol


class KlineDataError(ApplicationError):
    """K线数据错误"""
    
    def __init__(self, symbol: str, reason: str):
        super().__init__(f"股票 {symbol} 数据错误: {reason}", "KLINE_DATA_ERROR")
        self.symbol = symbol


class CollectionError(ApplicationError):
    """数据采集错误"""
    
    def __init__(self, symbol: str, reason: str):
        super().__init__(f"采集股票 {symbol} 失败: {reason}", "COLLECTION_ERROR")
        self.symbol = symbol
```

---

## application/kline_service.py K线应用服务

```python
"""K线应用服务

应用服务负责用例编排：
1. 接收路由层请求（DTO）
2. 调用领域服务或基础设施服务
3. 返回响应 DTO

应用服务本身不包含业务逻辑，业务逻辑在领域层。
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from domain.kline.entity import Kline, KlineCollection
from domain.kline.value_objects import StockCode
from domain.kline.repository import KlineRepository
from domain.kline.events import KlineCollected, KlineDeleted
from domain.stock_info.value_objects import StockCode as StockCodeVO

from infrastructure.collectors.base import Collector
from infrastructure.collectors.interfaces import CollectParams, FetcherProtocol
from infrastructure.repositories.kline_repository import KlineRepoImpl

from application.dto.kline import (
    KlineCollectRequest,
    KlineCollectResponse,
    KlineQueryRequest,
    KlineListResponse,
    KlineItemResponse,
    KlineDeleteRequest,
    KlineDeleteResponse,
)
from application.exceptions import KlineNotFoundError, CollectionError


class KlineAppService:
    """K线应用服务
    
    负责 K线相关的用例编排：
    - 采集K线
    - 查询K线
    - 删除K线
    """
    
    def __init__(
        self,
        session: AsyncSession,
        fetcher: Optional[FetcherProtocol] = None,
    ):
        self._session = session
        self._repo: KlineRepository = KlineRepoImpl(session)
        self._fetcher = fetcher  # 可选的采集器（测试时可不传入）
    
    # ── 采集用例 ────────────────────────────────────────────
    
    async def collect(
        self,
        request: KlineCollectRequest,
        fetcher: FetcherProtocol,
    ) -> KlineCollectResponse:
        """采集K线用例
        
        流程：
        1. 调用采集器获取数据
        2. 批量保存到数据库
        3. 发布领域事件
        """
        try:
            # Step 1: 调用采集器
            params = CollectParams(
                symbol=request.symbol,
                days=request.days,
                start_date=request.start_date,
                end_date=request.end_date,
            )
            raw_data = fetcher.fetch(params)
            
            if not raw_data:
                return KlineCollectResponse(
                    symbol=request.symbol,
                    name="",
                    saved_count=0,
                    total_count=0,
                    message="未获取到数据（代码无效或无交易记录）",
                )
            
            # Step 2: 转换为领域实体并批量保存
            klines = []
            name = ""
            for data in raw_data:
                kline = data.to_entity()
                klines.append(kline)
                if not name:
                    name = kline.name
            
            saved_count = await self._repo.save_batch(klines)
            
            # Step 3: 发布领域事件
            if klines:
                start = min(k.trade_date.date for k in klines)
                end = max(k.trade_date.date for k in klines)
                event = KlineCollected(
                    symbol=request.symbol,
                    name=name,
                    collected_count=saved_count,
                    total_count=len(klines),
                    start_date=start,
                    end_date=end,
                )
                # 事件发布（可由事件总线处理）
                # await self._event_bus.publish(event)
            
            return KlineCollectResponse(
                symbol=request.symbol,
                name=name,
                saved_count=saved_count,
                total_count=len(klines),
                message=f"成功采集 {saved_count} 条新数据（共获取 {len(klines)} 条）",
            )
            
        except Exception as e:
            raise CollectionError(request.symbol, str(e))
    
    async def collect_batch(
        self,
        symbols: list[str],
        days: int = 30,
        fetcher: FetcherProtocol,
    ) -> dict[str, KlineCollectResponse]:
        """批量采集多只股票"""
        results = {}
        for symbol in symbols:
            try:
                response = await self.collect(
                    KlineCollectRequest(symbol=symbol, days=days),
                    fetcher,
                )
                results[symbol] = response
            except Exception as e:
                results[symbol] = KlineCollectResponse(
                    symbol=symbol,
                    name="",
                    saved_count=-1,
                    total_count=0,
                    message=str(e),
                )
        return results
    
    # ── 查询用例 ────────────────────────────────────────────
    
    async def get_klines(
        self,
        request: KlineQueryRequest,
    ) -> KlineListResponse:
        """查询K线用例"""
        stock_code = StockCode(request.symbol)
        
        collection = await self._repo.find_by_symbol(
            symbol=stock_code,
            start_date=request.start_date,
            end_date=request.end_date,
            limit=request.limit,
            order_desc=request.order_desc,
        )
        
        items = [KlineItemResponse(
            symbol=k.symbol.code,
            name=k.name,
            date=k.trade_date.date,
            open=k.open,
            high=k.high,
            low=k.low,
            close=k.close,
            volume=k.volume,
            amount=k.amount,
            change_pct=k.change_pct,
        ) for k in collection.klines]
        
        return KlineListResponse(total=len(items), items=items)
    
    async def get_kline_by_date(
        self,
        symbol: str,
        trade_date: date,
    ) -> KlineItemResponse:
        """根据日期查询单条K线"""
        stock_code = StockCode(symbol)
        kline = await self._repo.find_by_symbol_date(stock_code, trade_date)
        
        if not kline:
            raise KlineNotFoundError(symbol, str(trade_date))
        
        return KlineItemResponse(
            symbol=kline.symbol.code,
            name=kline.name,
            date=kline.trade_date.date,
            open=kline.open,
            high=kline.high,
            low=kline.low,
            close=kline.close,
            volume=kline.volume,
            amount=kline.amount,
            change_pct=kline.change_pct,
        )
    
    async def get_stats(
        self,
        symbol: str,
    ) -> KlineStatsResponse:
        """获取K线统计"""
        stock_code = StockCode(symbol)
        
        count = await self._repo.count_by_symbol(stock_code)
        
        if count == 0:
            return KlineStatsResponse(
                symbol=symbol,
                name="",
                count=0,
            )
        
        collection = await self._repo.find_by_symbol(
            symbol=stock_code,
            limit=1,
            order_desc=True,
        )
        
        if not collection.klines:
            return KlineStatsResponse(symbol=symbol, name="", count=count)
        
        latest = collection.klines[0]
        start_date, end_date = collection.date_range
        
        return KlineStatsResponse(
            symbol=symbol,
            name=latest.name,
            count=count,
            start_date=start_date,
            end_date=end_date,
            latest_close=latest.close,
            latest_volume=latest.volume,
        )
    
    # ── 删除用例 ────────────────────────────────────────────
    
    async def delete(
        self,
        request: KlineDeleteRequest,
    ) -> KlineDeleteResponse:
        """删除K线用例"""
        stock_code = StockCode(request.symbol)
        
        if request.trade_date:
            # 删除单条
            deleted = await self._repo.delete_one(stock_code, request.trade_date)
            message = f"成功删除 {deleted} 条K线"
        else:
            # 删除全部
            deleted = await self._repo.delete_by_symbol(stock_code)
            message = f"成功删除股票 {request.symbol} 的全部 {deleted} 条K线"
        
        return KlineDeleteResponse(
            symbol=request.symbol,
            deleted_count=deleted,
            message=message,
        )
```

---

## application/stock_service.py 股票应用服务

```python
"""股票应用服务"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from domain.stock_info.entity import StockInfo
from domain.stock_info.value_objects import StockCode
from domain.stock_info.repository import StockInfoRepository
from domain.stock_info.events import StockInfoUpdated

from infrastructure.repositories.stock_repository import StockRepoImpl

from application.dto.stock import (
    StockUpdateRequest,
    StockItemResponse,
    StockListResponse,
    StockListItemResponse,
    StockDeleteResponse,
)
from application.exceptions import StockNotFoundError


class StockAppService:
    """股票应用服务
    
    负责股票信息的管理用例：
    - 查询股票列表
    - 查询股票详情
    - 更新股票信息
    """
    
    def __init__(self, session: AsyncSession):
        self._session = session
        self._repo: StockInfoRepository = StockRepoImpl(session)
    
    async def list_stocks(self) -> StockListResponse:
        """查询所有股票（含K线统计）"""
        rows = await self._repo.list_with_kline_stats()
        
        items = [StockListItemResponse(**row) for row in rows]
        return StockListResponse(total=len(items), items=items)
    
    async def get_stock(self, symbol: str) -> StockItemResponse:
        """查询股票详情"""
        stock_code = StockCode(symbol)
        stock = await self._repo.find_by_symbol(stock_code)
        
        if not stock:
            raise StockNotFoundError(symbol)
        
        return StockItemResponse(
            symbol=stock.symbol.code,
            name=stock.name,
            industry=stock.industry.name if stock.industry else None,
            market=stock.market.name if stock.market else None,
            list_date=stock.list_date,
            total_shares=stock.total_shares,
        )
    
    async def upsert_stock(
        self,
        symbol: str,
        name: str,
        industry: Optional[str] = None,
        market: Optional[str] = None,
    ) -> StockItemResponse:
        """新增或更新股票信息"""
        stock = StockInfo.create(
            symbol=symbol,
            name=name,
            industry=industry,
            market=market,
        )
        
        await self._repo.upsert(stock)
        
        return StockItemResponse(
            symbol=stock.symbol.code,
            name=stock.name,
            industry=industry,
            market=market,
        )
    
    async def update_stock(
        self,
        symbol: str,
        request: StockUpdateRequest,
    ) -> StockItemResponse:
        """更新股票信息"""
        stock_code = StockCode(symbol)
        stock = await self._repo.find_by_symbol(stock_code)
        
        if not stock:
            raise StockNotFoundError(symbol)
        
        if request.name is not None:
            stock.update_name(request.name)
        if request.industry is not None:
            stock.update_industry(request.industry)
        
        await self._repo.upsert(stock)
        
        return StockItemResponse(
            symbol=stock.symbol.code,
            name=stock.name,
            industry=stock.industry.name if stock.industry else None,
            market=stock.market.name if stock.market else None,
            list_date=stock.list_date,
            total_shares=stock.total_shares,
        )
    
    async def delete_stock(self, symbol: str) -> StockDeleteResponse:
        """删除股票"""
        stock_code = StockCode(symbol)
        success = await self._repo.delete(stock_code)
        
        if not success:
            raise StockNotFoundError(symbol)
        
        return StockDeleteResponse(
            symbol=symbol,
            deleted_count=1,
            message=f"成功删除股票 {symbol}",
        )
```

---

## application/__init__.py

```python
"""应用层导出"""

from application.kline_service import KlineAppService
from application.stock_service import StockAppService
from application.exceptions import (
    ApplicationError,
    KlineNotFoundError,
    StockNotFoundError,
    KlineDataError,
    CollectionError,
)

__all__ = [
    "KlineAppService",
    "StockAppService",
    "ApplicationError",
    "KlineNotFoundError",
    "StockNotFoundError",
    "KlineDataError",
    "CollectionError",
]
```

---

## 设计说明

### 应用服务 vs 领域服务

| 维度 | 应用服务 | 领域服务 |
|------|----------|----------|
| **职责** | 用例编排 | 业务规则实现 |
| **依赖** | 领域服务、基础设施 | 领域实体、值对象、仓储接口 |
| **状态** | 通常无状态 | 可有状态（聚合根） |
| **事务边界** | 可跨多个聚合 | 通常在单个聚合内 |

### 应用服务与仓储的关系

```
路由层 (Router)
    ↓
应用服务 (AppService) ← 接收 DTO
    ↓
领域服务/聚合根 (Domain) ← 执行业务逻辑
    ↓
仓储接口 (Repository) ← 定义持久化操作
    ↓
仓储实现 (RepoImpl) ← 执行 SQL
```

### 错误处理原则

- **应用服务不捕获业务异常**（如 `KlineNotFoundError`），让异常向上传播
- **应用服务捕获基础设施异常**（如数据库连接失败），转换为 `ApplicationError`
- **路由层统一处理异常**：由全局异常处理器返回标准错误响应

---

## 注意事项

1. **应用服务无状态**：应用服务不持有业务状态，只持有临时的工作数据（如 `AsyncSession`）
2. **DTO 转换在应用层**：DTO 与领域实体之间的转换在应用层完成，保持路由层简洁
3. **依赖注入**：应用服务通过构造函数接收依赖（仓储接口、采集器），便于测试
4. **事件发布**：应用服务在完成业务操作后发布领域事件，事件由事件总线异步处理
5. **批量操作容错**：`collect_batch` 在单只股票失败时继续处理其他股票，并将错误信息记录到响应中
