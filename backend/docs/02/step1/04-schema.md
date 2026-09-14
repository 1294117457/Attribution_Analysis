# 04 - schema 数据结构层

> 每个业务域在自己的 `schema.py` 中定义所有 Pydantic 模型。
> 按 DDD 分类：**BO**（业务对象/采集数据）、**DTO**（请求入参）、**VO**（响应视图）。

---

## Schema 分类说明

| 类型 | 英文 | 用途 | 使用位置 |
|------|------|------|---------|
| **BO** | Business Object | 采集器返回的数据、业务流转中间对象 | collector → service |
| **DTO** | Data Transfer Object | API 入参，接收前端请求体 | router（Request Body） |
| **VO** | View Object | API 出参，返回给前端 | router（Response） |

---

## kline/schema.py

```python
"""K线域 Schema（BO + DTO + VO）"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


# ════════════════════════════════════════════════════
# BO：采集数据（collector → service → repo）
# ════════════════════════════════════════════════════

class DailyKlineData(BaseModel):
    """日K线业务数据（采集层流转用）

    字段命名与 AkShare/Tushare 解析结果对齐。
    """
    symbol: str = Field(..., description="股票代码，如 000001")
    name: str = Field("", description="股票名称")
    trade_date: date = Field(..., description="交易日期")
    open: float = Field(..., description="开盘价（前复权）")
    high: float = Field(..., description="最高价（前复权）")
    low: float = Field(..., description="最低价（前复权）")
    close: float = Field(..., description="收盘价（前复权）")
    volume: int = Field(..., description="成交量（手）")
    amount: float = Field(..., description="成交额（元）")
    change_pct: Optional[float] = Field(None, description="涨跌幅 %")

    class Config:
        populate_by_name = True


# ════════════════════════════════════════════════════
# DTO：API 请求入参
# ════════════════════════════════════════════════════

class KlineCollectRequest(BaseModel):
    """POST /api/klines/collect 请求体"""
    symbol: str = Field(..., description="股票代码", examples=["000001"])
    days: int = Field(365, ge=1, le=3650, description="回溯天数")
    start_date: Optional[date] = Field(None, description="开始日期（优先于 days）")
    end_date: Optional[date] = Field(None, description="结束日期（默认今天）")


# ════════════════════════════════════════════════════
# VO：API 响应视图
# ════════════════════════════════════════════════════

class KlineVO(BaseModel):
    """单条 K 线视图（给前端 ECharts 用）"""
    symbol: str
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float
    change_pct: Optional[float] = None

    class Config:
        from_attributes = True  # 支持从 ORM 对象直接构建


class KlineListVO(BaseModel):
    """K线列表响应"""
    total: int
    items: list[KlineVO]


class KlineCollectVO(BaseModel):
    """采集结果响应"""
    symbol: str
    name: str
    saved_count: int
    message: str
```

---

## stock_info/schema.py

```python
"""股票信息域 Schema（BO + DTO + VO）"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


# ════════════════════════════════════════════════════
# VO：API 响应视图
# ════════════════════════════════════════════════════

class StockInfoVO(BaseModel):
    """单只股票详情"""
    symbol: str
    name: Optional[str] = None
    industry: Optional[str] = None
    market: Optional[str] = None
    list_date: Optional[date] = None
    total_shares: Optional[int] = None

    class Config:
        from_attributes = True


class StockListItemVO(BaseModel):
    """股票列表中的单项（含 K 线统计）"""
    symbol: str
    name: Optional[str] = None
    industry: Optional[str] = None
    market: Optional[str] = None
    record_count: int = 0
    kline_start: Optional[date] = None
    kline_end: Optional[date] = None


class StockListVO(BaseModel):
    """股票列表响应"""
    total: int
    items: list[StockListItemVO]
```

---

## indicators/schema.py

```python
"""技术指标 Schema（纯 VO，无 BO/DTO）"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel


class MAPoint(BaseModel):
    date: date
    ma5: Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    ma60: Optional[float] = None


class MACDPoint(BaseModel):
    date: date
    dif: Optional[float] = None
    dea: Optional[float] = None
    macd: Optional[float] = None     # histogram（柱状图值，= 2 × (DIF - DEA)）


class RSIPoint(BaseModel):
    date: date
    rsi6: Optional[float] = None
    rsi12: Optional[float] = None
    rsi24: Optional[float] = None


class IndicatorVO(BaseModel):
    """技术指标综合响应（一次返回所有指标）"""
    symbol: str
    ma: list[MAPoint] = []
    macd: list[MACDPoint] = []
    rsi: list[RSIPoint] = []
```

---

## 统一响应包装（app/response.py）

所有 API 统一用此格式包装，前端按 `code` 判断成功失败：

```python
"""统一 API 响应格式"""

from typing import Any, Optional
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: Any = None


def ok(data: Any = None, message: str = "success") -> dict:
    """成功响应（直接 return，FastAPI 自动序列化）"""
    return {"code": 200, "message": message, "data": data}


def err(message: str, code: int = 400) -> JSONResponse:
    """错误响应（返回非 200 状态码）"""
    return JSONResponse(
        status_code=code,
        content={"code": code, "message": message, "data": None},
    )
```

**路由使用示例：**

```python
# kline/router.py
from app import response as R

@router.get("/{symbol}")
async def get_klines(...):
    klines = await KlineService.get_klines(db, symbol, ...)
    vo = KlineListVO(total=len(klines), items=[KlineVO.model_validate(k) for k in klines])
    return R.ok(vo.model_dump())
```

---

## ORM → VO 转换规范

使用 `model_validate`（Pydantic v2）从 ORM 对象构建 VO，前提是 VO 设置了 `from_attributes = True`：

```python
# ✅ 正确：Pydantic v2 写法
kline_vo = KlineVO.model_validate(kline_db)

# ❌ 旧写法（Pydantic v1）
kline_vo = KlineVO.from_orm(kline_db)
```

**字段名不一致时**（ORM 的 `date` 对应 VO 的 `date`，`trade_date` 对应 BO 的 `trade_date`）：

```python
# KlineDB.date → KlineVO.date（字段名一致，直接 model_validate）
kline_vo = KlineVO.model_validate(kline_db)

# KlineData.trade_date → KlineDB.date（字段名不同，在 repo.save_batch 手动映射）
```

---

## 注意事项

1. **BO 不继承 ORM**：`DailyKlineData` 是纯 Pydantic，不是 SQLAlchemy Model
2. **VO 设置 `from_attributes = True`**：允许从 ORM 对象直接构建，避免手动 `dict()` 转换
3. **DTO 不需要 `from_attributes`**：DTO 只接收 JSON 请求体，不从 ORM 构建
4. **避免循环 import**：schema 文件只 import `pydantic`，不 import 任何其他域的模块
