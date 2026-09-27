# 01 - Domain 领域层

> 领域层是 DDD 的核心，包含所有业务概念、业务规则和业务逻辑。
> **领域层必须是纯净的**：不依赖任何外部框架（SQLAlchemy、FastAPI、Pydantic 等基础设施库）。

---

## 目录结构

```
src/domain/
├── __init__.py
├── base.py                 ← Entity 基类、ValueObject 基类
├── events.py               ← 通用的领域事件基类
│
├── kline/                  # K线聚合
│   ├── __init__.py
│   ├── value_objects.py    # StockCode、TradeDate、KlineId
│   ├── entity.py           # KlineAggregate（聚合根）
│   ├── schemas.py          # KlineVO、KlineBO
│   ├── events.py           # KlineCollected、KlineDeleted
│   └── repository.py       # KlineRepository 接口
│
└── stock_info/             # 股票信息聚合
    ├── __init__.py
    ├── value_objects.py     # StockCode
    ├── entity.py           # StockInfoAggregate
    ├── schemas.py          # StockInfoVO
    └── repository.py       # StockInfoRepository 接口
```

---

## domain/base.py 领域基类

```python
"""领域层基类

定义 Entity 和 ValueObject 的通用基类。
领域层不依赖任何外部框架（纯 Python）。
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, TypeVar, Generic


# ═══════════════════════════════════════════════════════════════════
# 实体基类
# ═══════════════════════════════════════════════════════════════════

@dataclass
class Entity(ABC):
    """实体基类
    
    实体具有唯一标识，其相等性基于标识而非属性。
    """
    
    @property
    @abstractmethod
    def id(self) -> Any:
        """返回实体的唯一标识"""
        ...
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        return hash(self.id)


T = TypeVar("T", bound=Entity)


@dataclass
class AggregateRoot(Entity, ABC):
    """聚合根基类
    
    聚合根是聚合内唯一可以外部引用的实体。
    聚合根负责维护聚合内对象的一致性。
    """
    
    @property
    def aggregate_id(self) -> str:
        """聚合的唯一标识（用于事件溯源）"""
        return f"{type(self).__name__}:{self.id}"
    
    # 内部事件列表（由聚合根收集）
    _domain_events: list[DomainEvent] = field(default_factory=list, init=False, repr=False)
    
    def add_event(self, event: DomainEvent) -> None:
        """添加领域事件"""
        self._domain_events.append(event)
    
    def clear_events(self) -> list[DomainEvent]:
        """获取并清除所有事件（用于发布）"""
        events = self._domain_events.copy()
        self._domain_events.clear()
        return events
    
    @property
    def domain_events(self) -> list[DomainEvent]:
        """获取所有未发布的领域事件"""
        return self._domain_events.copy()


# ═══════════════════════════════════════════════════════════════════
# 值对象基类
# ═══════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ValueObject(ABC):
    """值对象基类
    
    值对象无唯一标识，其相等性基于属性值。
    使用 frozen=True 使其不可变。
    """
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return False
        return self._get_values() == other._get_values()
    
    def __hash__(self) -> int:
        return hash(self._get_values())
    
    @abstractmethod
    def _get_values(self) -> tuple:
        """返回用于比较的属性元组"""
        ...


# ═══════════════════════════════════════════════════════════════════
# 领域事件基类
# ═══════════════════════════════════════════════════════════════════

@dataclass
class DomainEvent:
    """领域事件基类
    
    事件表示领域中已发生的重要业务事实。
    事件是不可变的，包含事件发生时的上下文信息。
    """
    
    occurred_on: datetime = field(default_factory=datetime.now)
    
    @property
    def event_type(self) -> str:
        return type(self).__name__


@dataclass
class TimestampedEvent(DomainEvent):
    """带时间戳的领域事件基类"""
    pass
```

---

## domain/events.py 通用事件

```python
"""通用领域事件定义"""

from dataclasses import dataclass, field
from datetime import datetime
from domain.base import DomainEvent


@dataclass
class KlineCollected(DomainEvent):
    """K线采集完成事件"""
    
    symbol: str
    count: int
    start_date: str
    end_date: str
    collected_at: datetime = field(default_factory=datetime.now)


@dataclass
class KlineDeleted(DomainEvent):
    """K线删除事件"""
    
    symbol: str
    date: str
    deleted_at: datetime = field(default_factory=datetime.now)


@dataclass
class StockInfoUpdated(DomainEvent):
    """股票信息更新事件"""
    
    symbol: str
    name: str
    updated_at: datetime = field(default_factory=datetime.now)
```

---

## domain/kline/ K线聚合

### value_objects.py 值对象

```python
"""K线领域值对象"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Optional

from domain.base import ValueObject


@dataclass(frozen=True)
class StockCode(ValueObject):
    """股票代码值对象
    
    股票代码格式验证：
    - A股：6位数字（000001、600000）
    - 创业板：6位数字（300xxx）
    - 科创板：6位数字（688xxx）
    """
    
    code: str
    
    def __post_init__(self) -> None:
        if not self._validate(self.code):
            raise ValueError(f"无效的股票代码: {self.code}")
    
    @staticmethod
    def _validate(code: str) -> bool:
        """验证股票代码格式"""
        if not code:
            return False
        # 6位数字
        if not re.match(r"^\d{6}$", code):
            return False
        return True
    
    def _get_values(self) -> tuple:
        return (self.code,)
    
    @property
    def is_shanghai(self) -> bool:
        """是否上海证券交易所"""
        return self.code.startswith(("6", "5"))
    
    @property
    def is_shenzhen(self) -> bool:
        """是否深圳证券交易所"""
        return self.code.startswith(("0", "3"))


@dataclass(frozen=True)
class TradeDate(ValueObject):
    """交易日期值对象
    
    封装日期验证和格式化逻辑。
    """
    
    date: date
    
    def _get_values(self) -> tuple:
        return (self.date,)
    
    @property
    def year(self) -> int:
        return self.date.year
    
    @property
    def month(self) -> int:
        return self.date.month
    
    @property
    def weekday(self) -> int:
        """0=Monday, 6=Sunday"""
        return self.date.weekday()
    
    @property
    def is_weekend(self) -> bool:
        return self.weekday >= 5
    
    def to_string(self, fmt: str = "%Y-%m-%d") -> str:
        """格式化日期字符串"""
        return self.date.strftime(fmt)


@dataclass(frozen=True)
class KlineData(ValueObject):
    """K线数据值对象
    
    封装一根K线的完整数据。
    用于传输和计算，不可变。
    """
    
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float
    change_pct: Optional[float] = None
    
    def _get_values(self) -> tuple:
        return (
            round(self.open, 3),
            round(self.high, 3),
            round(self.low, 3),
            round(self.close, 3),
            self.volume,
            round(self.amount, 2),
            self.change_pct,
        )
    
    @property
    def price_range(self) -> float:
        """价格振幅"""
        return self.high - self.low
    
    @property
    def change_amount(self) -> float:
        """涨跌额"""
        return self.close - self.open
    
    @property
    def turnover_rate(self) -> float:
        """换手率（需要成交量和总股本，这里仅作示例）"""
        if self.amount <= 0:
            return 0.0
        return round(self.amount / (self.volume * 100) if self.volume > 0 else 0, 4)
```

### entity.py K线聚合根

```python
"""K线聚合根"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from domain.base import AggregateRoot
from domain.kline.value_objects import StockCode, TradeDate, KlineData
from domain.kline.events import KlineCollected


@dataclass
class Kline(AggregateRoot):
    """K线聚合根
    
    K线是股票在特定日期的价格和交易量数据。
    聚合根维护K线的完整性和业务规则。
    """
    
    # 标识和基本信息
    id: int                          # 数据库主键
    symbol: StockCode                # 股票代码（值对象）
    trade_date: TradeDate            # 交易日期（值对象）
    name: str                        # 股票名称
    
    # 价格数据
    open: float                      # 开盘价
    high: float                      # 最高价
    low: float                       # 最低价
    close: float                     # 收盘价
    
    # 交易数据
    volume: int                      # 成交量（手）
    amount: float                    # 成交额（元）
    change_pct: Optional[float]      # 涨跌幅（%）
    
    # 元数据
    created_at: Optional[date] = None
    updated_at: Optional[date] = None
    
    @property
    def kline_data(self) -> KlineData:
        """获取K线数据值对象"""
        return KlineData(
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
            volume=self.volume,
            amount=self.amount,
            change_pct=self.change_pct,
        )
    
    @property
    def is_up(self) -> bool:
        """是否上涨"""
        return self.close > self.open
    
    @property
    def is_down(self) -> bool:
        """是否下跌"""
        return self.close < self.open
    
    @property
    def price_range(self) -> float:
        """价格振幅"""
        return self.high - self.low
    
    @property
    def amplitude(self) -> float:
        """振幅百分比"""
        if self.open == 0:
            return 0.0
        return round((self.high - self.low) / self.open * 100, 2)
    
    @property
    def turnover(self) -> float:
        """成交额/成交量（平均成交价）"""
        return round(self.amount / self.volume, 2) if self.volume > 0 else 0.0
    
    def validate(self) -> bool:
        """验证K线数据合法性"""
        errors: list[str] = []
        
        if self.high < self.low:
            errors.append("最高价不能低于最低价")
        if self.high < self.open or self.high < self.close:
            errors.append("最高价不能低于开盘价或收盘价")
        if self.low > self.open or self.low > self.close:
            errors.append("最低价不能高于开盘价或收盘价")
        if self.volume < 0:
            errors.append("成交量不能为负")
        if self.amount < 0:
            errors.append("成交额不能为负")
        
        if errors:
            raise ValueError(f"K线数据验证失败: {'; '.join(errors)}")
        
        return True
    
    @classmethod
    def create(
        cls,
        symbol: str,
        name: str,
        trade_date: date,
        open: float,
        high: float,
        low: float,
        close: float,
        volume: int,
        amount: float,
        change_pct: Optional[float] = None,
        id: int = 0,
    ) -> Kline:
        """工厂方法：创建K线聚合根"""
        kline = cls(
            id=id,
            symbol=StockCode(symbol),
            trade_date=TradeDate(trade_date),
            name=name,
            open=open,
            high=high,
            low=low,
            close=close,
            volume=volume,
            amount=amount,
            change_pct=change_pct,
        )
        kline.validate()
        return kline
    
    @classmethod
    def from_data(
        cls,
        symbol: str,
        name: str,
        trade_date: date,
        open: float,
        high: float,
        low: float,
        close: float,
        volume: int,
        amount: float,
        change_pct: Optional[float] = None,
        id: int = 0,
    ) -> Kline:
        """工厂方法：从采集数据创建K线"""
        return cls.create(
            symbol=symbol,
            name=name,
            trade_date=trade_date,
            open=open,
            high=high,
            low=low,
            close=close,
            volume=volume,
            amount=amount,
            change_pct=change_pct,
            id=id,
        )


@dataclass
class KlineCollection:
    """K线集合（值对象）
    
    用于批量处理一组K线。
    """
    
    symbol: StockCode
    klines: list[Kline] = field(default_factory=list)
    
    @property
    def count(self) -> int:
        return len(self.klines)
    
    @property
    def date_range(self) -> tuple[Optional[date], Optional[date]]:
        """获取日期范围"""
        if not self.klines:
            return None, None
        dates = [k.trade_date.date for k in self.klines]
        return min(dates), max(dates)
    
    def add(self, kline: Kline) -> None:
        """添加K线（自动验证股票代码一致性）"""
        if kline.symbol != self.symbol:
            raise ValueError(
                f"股票代码不一致: {self.symbol.code} != {kline.symbol.code}"
            )
        self.klines.append(kline)
    
    def sort_by_date(self, reverse: bool = False) -> KlineCollection:
        """按日期排序"""
        sorted_klines = sorted(self.klines, key=lambda k: k.trade_date.date, reverse=reverse)
        return KlineCollection(symbol=self.symbol, klines=sorted_klines)
```

### schemas.py 领域 Schema

```python
"""K线领域 Schema（BO/VO）

注意：这里的 Schema 仅用于领域层内部数据传输。
API 层的 DTO 放在 application 层。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════
# BO (Business Object)：业务对象
# 用于采集器返回的数据，是业务流转的中间对象
# ═══════════════════════════════════════════════════════════════════

class KlineBO(BaseModel):
    """K线业务对象（采集层 → 应用层）
    
    用于 AkShare 采集后的原始数据结构。
    字段名与外部数据源对齐。
    """
    symbol: str = Field(..., description="股票代码")
    name: str = Field("", description="股票名称")
    trade_date: date = Field(..., description="交易日期")
    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    close: float = Field(..., description="收盘价")
    volume: int = Field(..., description="成交量（手）")
    amount: float = Field(..., description="成交额（元）")
    change_pct: Optional[float] = Field(None, description="涨跌幅 %")
    
    model_config = {"populate_by_name": True}
    
    def to_entity(self, id: int = 0) -> Kline:
        """转换为领域实体"""
        return Kline.from_data(
            symbol=self.symbol,
            name=self.name,
            trade_date=self.trade_date,
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
            volume=self.volume,
            amount=self.amount,
            change_pct=self.change_pct,
            id=id,
        )


# ═══════════════════════════════════════════════════════════════════
# VO (View Object)：视图对象
# 用于领域层到应用层的数据传输
# ═══════════════════════════════════════════════════════════════════

class KlineVO(BaseModel):
    """K线视图对象（领域层 → 应用层 → 路由层）
    
    用于 API 响应的标准化数据结构。
    支持从 ORM 对象和领域实体构建。
    """
    symbol: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    date: date = Field(..., description="交易日期")
    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    close: float = Field(..., description="收盘价")
    volume: int = Field(..., description="成交量（手）")
    amount: float = Field(..., description="成交额（元）")
    change_pct: Optional[float] = Field(None, description="涨跌幅 %")
    
    model_config = {"from_attributes": True}
    
    @classmethod
    def from_entity(cls, kline: Kline) -> KlineVO:
        """从领域实体构建"""
        return cls(
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


class KlineListVO(BaseModel):
    """K线列表视图"""
    total: int
    items: list[KlineVO]


class KlineStatsVO(BaseModel):
    """K线统计视图"""
    symbol: str
    name: str
    count: int = 0
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    latest_close: Optional[float] = None
    latest_volume: Optional[int] = None
```

### events.py K线领域事件

```python
"""K线领域事件"""

from dataclasses import dataclass, field
from datetime import date, datetime

from domain.base import DomainEvent


@dataclass
class KlineCollected(DomainEvent):
    """K线采集完成事件
    
    触发时机：成功从外部数据源采集并保存K线后。
    用途：
    - 记录采集日志
    - 触发缓存更新
    - 触发后续分析任务
    """
    
    symbol: str
    name: str
    collected_count: int
    total_count: int           # 采集到的总条数（包含已存在的）
    start_date: date
    end_date: date
    source: str = "akshare"   # 数据来源
    
    occurred_on: datetime = field(default_factory=datetime.now)
    
    @property
    def is_new_data(self) -> bool:
        """是否有新增数据"""
        return self.collected_count > 0


@dataclass
class KlineDeleted(DomainEvent):
    """K线删除事件"""
    
    symbol: str
    date: Optional[date] = None  # None 表示删除全部
    deleted_count: int = 0
    
    occurred_on: datetime = field(default_factory=datetime.now)


@dataclass
class KlineQueryRequested(DomainEvent):
    """K线查询请求事件"""
    
    symbol: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    limit: int = 365
    
    occurred_on: datetime = field(default_factory=datetime.now)
```

### repository.py K线仓储接口

```python
"""K线仓储接口

仓储接口定义在领域层，实现放在基础设施层。
这样领域层完全不依赖数据库细节。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Protocol, Optional

from domain.kline.entity import Kline, KlineCollection
from domain.kline.value_objects import StockCode


class KlineRepository(Protocol):
    """K线仓储接口
    
    定义K线数据的持久化操作。
    实现类放在 infrastructure/repositories/
    """
    
    async def save(self, kline: Kline) -> Kline:
        """保存单条K线（存在则更新）"""
        ...
    
    async def save_batch(self, klines: list[Kline]) -> int:
        """批量保存K线，返回实际新增条数"""
        ...
    
    async def find_by_id(self, id: int) -> Optional[Kline]:
        """根据ID查询"""
        ...
    
    async def find_by_symbol_date(
        self, 
        symbol: StockCode, 
        trade_date: date
    ) -> Optional[Kline]:
        """根据股票代码和日期查询"""
        ...
    
    async def find_by_symbol(
        self,
        symbol: StockCode,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 365,
        order_desc: bool = True,
    ) -> KlineCollection:
        """根据股票代码查询K线列表"""
        ...
    
    async def count_by_symbol(self, symbol: StockCode) -> int:
        """统计某股票的K线条数"""
        ...
    
    async def delete_by_symbol(self, symbol: StockCode) -> int:
        """删除某股票的所有K线，返回删除条数"""
        ...
    
    async def delete_one(self, symbol: StockCode, trade_date: date) -> int:
        """删除单条K线，返回是否成功"""
        ...
    
    async def exists(self, symbol: StockCode, trade_date: date) -> bool:
        """检查K线是否存在"""
        ...
```

---

## domain/stock_info/ 股票信息聚合

### value_objects.py 值对象

```python
"""股票信息值对象"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from domain.base import ValueObject


@dataclass(frozen=True)
class Industry(ValueObject):
    """行业值对象"""
    
    name: str
    
    def _get_values(self) -> tuple:
        return (self.name,)
    
    @property
    def is_valid(self) -> bool:
        return bool(self.name and self.name.strip())


@dataclass(frozen=True)
class Market(ValueObject):
    """市场值对象
    
    标识股票所属交易所。
    """
    
    code: str
    name: str
    
    SHANGHAI = Market("SH", "上海证券交易所")
    SHENZHEN = Market("SZ", "深圳证券交易所")
    BSE = Market("BSE", "北京证券交易所")
    
    def _get_values(self) -> tuple:
        return (self.code, self.name)
    
    @property
    def is_shanghai(self) -> bool:
        return self.code == "SH"
    
    @property
    def is_shenzhen(self) -> bool:
        return self.code in ("SZ", "BSE")
    
    @classmethod
    def from_code(cls, code: str) -> Market:
        """根据代码获取市场"""
        markets = {
            "SH": cls.SHANGHAI,
            "SZ": cls.SHENZHEN,
            "BSE": cls.BSE,
        }
        return markets.get(code.upper(), cls.SHENZHEN)
```

### entity.py 股票信息聚合根

```python
"""股票信息聚合根"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from domain.base import AggregateRoot
from domain.stock_info.value_objects import Industry, Market, StockCode as StockCodeVO


@dataclass
class StockInfo(AggregateRoot):
    """股票信息聚合根
    
    维护股票的基本信息和元数据。
    """
    
    id: int                          # 数据库主键
    symbol: StockCodeVO              # 股票代码
    name: str                        # 股票名称
    industry: Optional[Industry]     # 所属行业
    market: Optional[Market]         # 所属市场
    list_date: Optional[date]        # 上市日期
    total_shares: Optional[int]      # 总股本（万股）
    
    created_at: Optional[date] = None
    updated_at: Optional[date] = None
    
    @classmethod
    def create(
        cls,
        symbol: str,
        name: str,
        industry: Optional[str] = None,
        market: Optional[str] = None,
        list_date: Optional[date] = None,
        total_shares: Optional[int] = None,
        id: int = 0,
    ) -> StockInfo:
        """工厂方法：创建股票信息"""
        return cls(
            id=id,
            symbol=StockCodeVO(symbol),
            name=name,
            industry=Industry(industry) if industry else None,
            market=Market.from_code(market) if market else None,
            list_date=list_date,
            total_shares=total_shares,
        )
    
    def update_name(self, name: str) -> None:
        """更新股票名称"""
        self.name = name
        self.add_event(StockInfoUpdated(
            symbol=self.symbol.code,
            name=name,
        ))
    
    def update_industry(self, industry: str) -> None:
        """更新所属行业"""
        self.industry = Industry(industry)
```

### schemas.py 股票信息 Schema

```python
"""股票信息领域 Schema"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class StockInfoVO(BaseModel):
    """股票信息视图对象"""
    
    symbol: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    industry: Optional[str] = Field(None, description="所属行业")
    market: Optional[str] = Field(None, description="所属市场")
    list_date: Optional[date] = Field(None, description="上市日期")
    total_shares: Optional[int] = Field(None, description="总股本（万股）")
    
    model_config = {"from_attributes": True}
    
    @classmethod
    def from_entity(cls, entity: StockInfo) -> StockInfoVO:
        return cls(
            symbol=entity.symbol.code,
            name=entity.name,
            industry=entity.industry.name if entity.industry else None,
            market=entity.market.name if entity.market else None,
            list_date=entity.list_date,
            total_shares=entity.total_shares,
        )


class StockListItemVO(BaseModel):
    """股票列表项视图（含K线统计）"""
    
    symbol: str
    name: Optional[str] = None
    industry: Optional[str] = None
    market: Optional[str] = None
    record_count: int = 0
    kline_start: Optional[date] = None
    kline_end: Optional[date] = None


class StockListVO(BaseModel):
    """股票列表视图"""
    total: int
    items: list[StockListItemVO]
```

### repository.py 股票信息仓储接口

```python
"""股票信息仓储接口"""

from __future__ import annotations

from abc import abstractmethod
from datetime import date
from typing import Protocol, Optional

from domain.stock_info.entity import StockInfo
from domain.stock_info.value_objects import StockCode


class StockInfoRepository(Protocol):
    """股票信息仓储接口"""
    
    async def save(self, stock: StockInfo) -> StockInfo:
        """保存股票信息"""
        ...
    
    async def find_by_symbol(self, symbol: StockCode) -> Optional[StockInfo]:
        """根据股票代码查询"""
        ...
    
    async def find_all(self) -> list[StockInfo]:
        """查询所有股票"""
        ...
    
    async def upsert(self, stock: StockInfo) -> StockInfo:
        """插入或更新"""
        ...
    
    async def delete(self, symbol: StockCode) -> bool:
        """删除股票"""
        ...
    
    async def list_with_kline_stats(self) -> list[dict]:
        """查询所有股票（含K线统计）"""
        ...
```

---

## domain/__init__.py

```python
"""领域层导出"""

# 基类
from domain.base import (
    Entity,
    AggregateRoot,
    ValueObject,
    DomainEvent,
    TimestampedEvent,
)

# 通用事件
from domain.events import (
    KlineCollected,
    KlineDeleted,
    StockInfoUpdated,
)

# K线聚合
from domain.kline.entity import Kline, KlineCollection
from domain.kline.value_objects import StockCode, TradeDate, KlineData
from domain.kline.schemas import KlineBO, KlineVO, KlineListVO, KlineStatsVO
from domain.kline.repository import KlineRepository
from domain.kline.events import KlineCollected, KlineDeleted, KlineQueryRequested

# 股票信息聚合
from domain.stock_info.entity import StockInfo
from domain.stock_info.value_objects import Industry, Market
from domain.stock_info.schemas import StockInfoVO, StockListItemVO, StockListVO
from domain.stock_info.repository import StockInfoRepository

__all__ = [
    # 基类
    "Entity",
    "AggregateRoot", 
    "ValueObject",
    "DomainEvent",
    "TimestampedEvent",
    # K线
    "Kline",
    "KlineCollection",
    "StockCode",
    "TradeDate",
    "KlineData",
    "KlineBO",
    "KlineVO",
    "KlineListVO",
    "KlineStatsVO",
    "KlineRepository",
    "KlineCollected",
    "KlineDeleted",
    "KlineQueryRequested",
    # 股票信息
    "StockInfo",
    "Industry",
    "Market",
    "StockInfoVO",
    "StockListItemVO",
    "StockListVO",
    "StockInfoRepository",
    "StockInfoUpdated",
]
```

---

## 注意事项

1. **领域层纯净性**：领域层只使用 Python 标准库和类型注解（`typing`），不依赖 SQLAlchemy、FastAPI、Pydantic
2. **值对象不可变**：使用 `@dataclass(frozen=True)` 确保值对象不可变
3. **聚合根收集事件**：通过 `_domain_events` 列表收集领域事件，外部通过 `domain_events` 属性获取
4. **仓储接口分离**：Repository 接口定义在领域层，实现放在基础设施层，通过依赖注入组合
5. **Schema 分层**：
   - `BO`（Business Object）：采集层返回的原始数据
   - `VO`（View Object）：领域层到应用层的数据传输
   - DTO 放在应用层（见 `application/dto/`）
