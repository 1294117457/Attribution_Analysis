# 05 - service 业务逻辑层

> 职责：业务编排——调用 Repo 做持久化，调用 Collector 做数据采集，**不直接写 SQL**，**不直接调 AkShare**。
> 所有 service 方法都是 `async def`，接收 `AsyncSession` 参数（从 router 注入）。

---

## kline/service.py

```python
"""K线业务服务"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from collectors.collector import Collector
from collectors.akshare import AkShareFetcher
from collectors.interfaces.fetcher import CollectParams
from kline.model import DailyKlineDB
from kline.repo import KlineRepo
from kline.schema import DailyKlineData, KlineVO, KlineListVO, KlineCollectVO
from stock_info.service import StockInfoService


class KlineService:
    """K线域业务编排

    依赖：
        - KlineRepo（持久化）
        - StockInfoService（维护股票基本信息，采集时同步更新）
        - Collector + AkShareFetcher（外部数据采集）

    方法全部为静态方法，接收 db 参数，便于测试和组合调用。
    """

    # ── 查询 ────────────────────────────────────────────────

    @staticmethod
    async def get_klines(
        db: AsyncSession,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 365,
        order_asc: bool = True,
    ) -> list[DailyKlineDB]:
        """从数据库查询 K 线，供 API 和指标计算使用"""
        return await KlineRepo.query(
            db, symbol, start_date, end_date, limit, order_asc
        )

    # ── 采集 ────────────────────────────────────────────────

    @staticmethod
    async def collect_and_save(
        db: AsyncSession,
        symbol: str,
        days: int = 365,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> KlineCollectVO:
        """采集日K线并存入数据库。

        流程：
            1. 调用 AkShareFetcher 拉取数据
            2. 调用 StockInfoService 同步股票基本信息
            3. 调用 KlineRepo.save_batch 批量去重写入
        """
        # Step 1: 采集
        collector = Collector(AkShareFetcher(DailyKlineData))
        params = CollectParams(
            symbol=symbol,
            days=days,
            start_date=start_date,
            end_date=end_date,
        )
        klines: list[DailyKlineData] = collector.collect(params)

        if not klines:
            return KlineCollectVO(
                symbol=symbol,
                name="",
                saved_count=0,
                message="未获取到数据（代码无效或无交易记录）",
            )

        stock_name = klines[0].name if klines else ""

        # Step 2: 同步股票基本信息
        await StockInfoService.upsert(db, symbol=symbol, name=stock_name)

        # Step 3: 批量写入（去重）
        saved_count = await KlineRepo.save_batch(db, klines)

        return KlineCollectVO(
            symbol=symbol,
            name=stock_name,
            saved_count=saved_count,
            message=f"成功采集 {saved_count} 条新数据（共获取 {len(klines)} 条）",
        )

    @staticmethod
    async def collect_batch(
        db: AsyncSession,
        symbols: list[str],
        days: int = 30,
    ) -> dict[str, int]:
        """批量采集多只股票，返回 {symbol: saved_count}"""
        results: dict[str, int] = {}
        for symbol in symbols:
            try:
                vo = await KlineService.collect_and_save(db, symbol, days=days)
                results[symbol] = vo.saved_count
            except Exception as e:
                # 单只失败不影响其他股票
                results[symbol] = -1
        return results

    # ── 删除 ────────────────────────────────────────────────

    @staticmethod
    async def delete_by_symbol(db: AsyncSession, symbol: str) -> int:
        return await KlineRepo.delete_by_symbol(db, symbol)

    @staticmethod
    async def delete_one(db: AsyncSession, symbol: str, trade_date: date) -> int:
        return await KlineRepo.delete_one(db, symbol, trade_date)
```

---

## stock_info/service.py

```python
"""股票信息业务服务"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from stock_info.model import StockInfoDB
from stock_info.repo import StockInfoRepo
from stock_info.schema import StockInfoVO, StockListItemVO, StockListVO


class StockInfoService:

    @staticmethod
    async def get(db: AsyncSession, symbol: str) -> Optional[StockInfoDB]:
        return await StockInfoRepo.get_by_symbol(db, symbol)

    @staticmethod
    async def list_stocks(db: AsyncSession) -> StockListVO:
        """返回所有已采集股票列表（含 K 线统计数量）"""
        rows = await StockInfoRepo.list_with_kline_stats(db)
        items = [StockListItemVO(**row) for row in rows]
        return StockListVO(total=len(items), items=items)

    @staticmethod
    async def upsert(
        db: AsyncSession,
        symbol: str,
        name: str,
        industry: Optional[str] = None,
        market: Optional[str] = None,
    ) -> None:
        """插入或更新股票信息（采集时同步调用）"""
        await StockInfoRepo.upsert(db, symbol, name, industry, market)
```

---

## indicators/service.py

```python
"""技术指标业务服务（纯计算，不采集，不存储）"""

from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from kline.service import KlineService
from indicators.calculator import IndicatorCalculator
from indicators.schema import IndicatorVO


class IndicatorService:

    @staticmethod
    async def get_indicators(
        db: AsyncSession,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> IndicatorVO:
        """从 DB 读取 K 线，计算技术指标并返回"""

        # 指标计算需要足够的历史数据（至少 60 日，用于 MA60）
        klines = await KlineService.get_klines(
            db, symbol, start_date, end_date, limit=500, order_asc=True
        )

        if not klines:
            return IndicatorVO(symbol=symbol)

        df = pd.DataFrame([
            {
                "date": k.date,
                "open": k.open,
                "high": k.high,
                "low": k.low,
                "close": k.close,
                "volume": k.volume,
            }
            for k in klines
        ]).set_index("date")

        calc = IndicatorCalculator(df)
        return IndicatorVO(
            symbol=symbol,
            ma=calc.ma(),
            macd=calc.macd(),
            rsi=calc.rsi(),
        )
```

---

## 设计说明

### 为什么用静态方法？

参考 ID 项目的 Repo 层风格，Service 方法也采用静态方法：

```python
# 静态方法：调用时显式传入 db，便于测试 mock
await KlineService.get_klines(db, symbol="000001")

# 实例方法：db 存在实例上，测试时需要构造整个 Service 对象
service = KlineService(db)
await service.get_klines(symbol="000001")
```

两种方式都可行，选静态方法的优势是**测试更简单**，直接 mock `db` 传入即可。

### KlineService 调用 StockInfoService

采集 K 线时同步更新股票信息，通过**直接调用**另一个域的 service（可接受）：

```python
# kline/service.py 调用 stock_info/service.py
await StockInfoService.upsert(db, symbol=symbol, name=stock_name)
```

这是 **kline → stock_info** 的单向调用，符合依赖方向（kline 依赖 stock_info，不反向）。

### 错误处理原则

- Service 层**不捕获异常**（除批量操作的单项容错）
- 让异常向上冒泡到 Router 层
- Router 层也**不捕获**，由全局 exception handler 统一处理
- 只有需要容错的批量操作（`collect_batch`）在 Service 内部 try/except

```python
# ✅ 批量操作内部容错
for symbol in symbols:
    try:
        vo = await KlineService.collect_and_save(db, symbol)
        results[symbol] = vo.saved_count
    except Exception:
        results[symbol] = -1   # 单只失败不影响其他

# ❌ 不要在普通方法里吞异常
async def get_klines(...):
    try:
        return await KlineRepo.query(...)
    except Exception:
        return []  # 不要这样，会掩盖真实错误
```
