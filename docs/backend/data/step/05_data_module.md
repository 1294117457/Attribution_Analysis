# Step 5: Data 数据采集模块

## 1. 目录结构

```
backend/
├── data/
│   ├── __init__.py          # 模块导出
│   ├── schemas.py           # Pydantic 数据模型
│   ├── akshare_client.py    # AkShare 客户端
│   └── service.py           # 采集服务
```

---

## 2. 创建数据模型

### 2.1 data/schemas.py

```python
"""数据采集模块的 Pydantic 模型"""

from pydantic import BaseModel, Field
from datetime import date
from typing import Optional


class StockKline(BaseModel):
    """K 线数据"""

    symbol: str = Field(..., description="股票代码")
    name: str = Field("", description="股票名称")
    date: date = Field(..., description="日期")
    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    close: float = Field(..., description="收盘价")
    volume: int = Field(..., description="成交量")
    amount: float = Field(..., description="成交额")
    change_pct: Optional[float] = Field(None, description="涨跌幅 %")


class StockKlineResponse(BaseModel):
    """K 线数据响应 (从数据库读取)"""

    id: int
    symbol: str
    name: Optional[str] = None
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float
    change_pct: Optional[float] = None

    class Config:
        from_attributes = True


class CollectResponse(BaseModel):
    """采集响应"""

    status: str  # success, failed, partial
    symbol: str
    count: int
    message: str
```

### 2.2 data/__init__.py

```python
"""数据采集模块"""

from data.schemas import StockKline, StockKlineResponse
from data.akshare_client import AkShareClient
from data.service import DataService

__all__ = [
    "StockKline",
    "StockKlineResponse",
    "AkShareClient",
    "DataService",
]
```

---

## 3. 创建 AkShare 客户端

### 3.1 data/akshare_client.py

```python
"""AkShare 数据获取客户端"""

import akshare as ak
import pandas as pd
from datetime import date
from typing import Optional

from data.schemas import StockKline


class AkShareClient:
    """AkShare 数据客户端"""

    def get_stock_kline(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        adjust: str = "qfq",
    ) -> list[StockKline]:
        """
        获取股票 K 线数据

        Args:
            symbol: 股票代码，如 "000001"
            start_date: 开始日期
            end_date: 结束日期
            adjust: 复权类型，"qfq" 前复权，"hfq" 后复权，"" 不复权

        Returns:
            list[StockKline]
        """
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")

        df = ak.stock_zh_a_hist(
            symbol=symbol,
            start_date=start_str,
            end_date=end_str,
            adjust=adjust,
        )

        return self._parse_dataframe(df, symbol)

    def get_stock_name(self, symbol: str) -> str:
        """获取股票名称"""
        df = ak.stock_zh_a_spot_em()
        row = df[df["代码"] == symbol]
        if not row.empty:
            return row.iloc[0]["名称"]
        return ""

    def _parse_dataframe(self, df: pd.DataFrame, symbol: str) -> list[StockKline]:
        """解析 DataFrame 为 StockKline 列表"""
        klines = []

        for _, row in df.iterrows():
            try:
                raw_date = row["日期"]
                if isinstance(raw_date, str):
                    kline_date = date.fromisoformat(raw_date)
                else:
                    kline_date = pd.to_datetime(raw_date).date()

                change_pct = row.get("涨跌幅")
                if change_pct == "--":
                    change_pct = None

                kline = StockKline(
                    symbol=symbol,
                    name="",
                    date=kline_date,
                    open=float(row["开盘"]),
                    high=float(row["最高"]),
                    low=float(row["最低"]),
                    close=float(row["收盘"]),
                    volume=int(row["成交量"]),
                    amount=float(row["成交额"]),
                    change_pct=float(change_pct) if change_pct else None,
                )
                klines.append(kline)
            except Exception:
                continue

        return klines
```

---

## 4. 创建数据服务

### 4.1 data/service.py

```python
"""数据采集服务"""

from datetime import date, timedelta
from typing import Optional

from data.akshare_client import AkShareClient
from data.schemas import StockKline


class DataService:
    """数据服务"""

    def __init__(self):
        self.client = AkShareClient()

    def collect_stock(
        self,
        symbol: str,
        days: int = 365,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[StockKline]:
        """采集股票数据"""
        if end_date is None:
            end_date = date.today()

        if start_date is None:
            start_date = end_date - timedelta(days=days)

        # 获取股票名称
        name = self.client.get_stock_name(symbol)

        # 获取 K 线数据
        klines = self.client.get_stock_kline(symbol, start_date, end_date)

        # 补充股票名称
        for kline in klines:
            kline.name = name

        return klines

    def collect_batch(
        self,
        symbols: list[str],
        days: int = 30,
    ) -> dict[str, list[StockKline]]:
        """批量采集股票数据"""
        results = {}

        for symbol in symbols:
            try:
                klines = self.collect_stock(symbol, days)
                results[symbol] = klines
            except Exception as e:
                print(f"采集 {symbol} 失败: {e}")
                results[symbol] = []

        return results
```

---

## 5. 验证数据采集

### 5.1 test_data.py

```python
"""测试数据采集"""

from datetime import date, timedelta
from data.akshare_client import AkShareClient
from data.service import DataService


def test_get_stock_kline():
    """测试获取 K 线数据"""
    client = AkShareClient()

    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    klines = client.get_stock_kline("000001", start_date, end_date)

    print(f"获取到 {len(klines)} 条数据")
    if klines:
        print(f"最新数据: {klines[0]}")

    assert len(klines) > 0, "应该获取到数据"
    print("✅ test_get_stock_kline 通过!")


def test_get_stock_name():
    """测试获取股票名称"""
    client = AkShareClient()
    name = client.get_stock_name("000001")
    print(f"股票名称: {name}")
    assert name, "应该获取到股票名称"
    print("✅ test_get_stock_name 通过!")


def test_data_service():
    """测试数据服务"""
    service = DataService()
    klines = service.collect_stock("000001", days=7)

    print(f"采集到 {len(klines)} 条数据")
    if klines:
        kline = klines[0]
        print(f"代码: {kline.symbol}, 名称: {kline.name}")
        print(f"日期: {kline.date}, 收盘: {kline.close}")

    assert len(klines) > 0
    print("✅ test_data_service 通过!")


if __name__ == "__main__":
    test_get_stock_kline()
    test_get_stock_name()
    test_data_service()
    print("\n🎉 所有测试通过!")
```

### 5.2 运行测试

```bash
cd backend
python test_data.py
```

---

## 6. 常见问题

### Q: AkShare 返回空数据？

检查：
1. 股票代码是否正确（6 位数字）
2. 日期范围是否合理
3. 市场是否正确（沪深需要不带后缀）

### Q: 复权类型怎么选？

| 类型 | 说明 | 适用场景 |
|------|------|----------|
| qfq | 前复权 | 技术分析、异常检测 |
| hfq | 后复权 | 基本面分析 |
| "" | 不复权 | 原始价格展示 |

### Q: 如何获取实时行情？

```python
# 实时行情
df = ak.stock_zh_a_spot_em()  # 所有A股实时行情
df = ak.stock_zh_a_spot_sina(symbol="sz000001")  # 单只股票
```
