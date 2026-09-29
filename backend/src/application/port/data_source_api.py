"""统一数据源 API 协议（L1）

设计原则：
  - **1 个顶层 DataSourceAPI 协议**（统一所有数据源形态）
  - **6 个细粒度业务协议**（KlineAPI / DailyBasicAPI / StockBasicAPI /
    FinReportAPI / ConceptAPI / MinuteKlineAPI）按业务切，编译期可检查
  - **所有方法 async def**（同步阻塞实现内部 asyncio.to_thread）
  - **所有方法返回 CallResult**（不靠 raise 表达错误，编排层统一处理）
  - **方法签名 = 业务参数**（symbol / trade_date / ts_code），不传 BO / 不传请求对象
    参数处理由编排层 Pipeline + UnitResolver 负责

任何数据源（Tushare / Adata / Pytdx / Wind / Choice...）
只要实现 DataSourceAPI + 对应业务协议，就能被编排调度层无差别调用。

**P0 设计要点**（用户确认）：
- 6 个老 Protocol（KlineFetcher / DailyBasicFetcher / ...）已删除
- 新统一协议名为 KlineAPI / DailyBasicAPI / ...（带 API 后缀，与老 fetcher 区分）
- 不考虑兼容性
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


# ═══════════════════════════════════════════════════════════════════════
# 统一返回
# ═══════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class CallResult:
    """统一返回：成功/失败 + 数据 + 元信息

    编排层统一检查 ok 字段；失败不靠 raise。
    """

    ok: bool
    data: Any = None                # BO 列表 / dict / 单值
    error: str | None = None
    error_type: str | None = None   # "rate_limited" / "auth" / "network" / "other"
    elapsed_ms: int = 0
    source: str = ""                # "Tushare" / "Adata" / "Pytdx"

    @classmethod
    def success(cls, data: Any, *, source: str = "", elapsed_ms: int = 0) -> "CallResult":
        return cls(ok=True, data=data, source=source, elapsed_ms=elapsed_ms)

    @classmethod
    def failure(
        cls,
        error: str,
        *,
        source: str = "",
        error_type: str = "other",
        elapsed_ms: int = 0,
    ) -> "CallResult":
        return cls(
            ok=False,
            error=error,
            error_type=error_type,
            source=source,
            elapsed_ms=elapsed_ms,
        )


# ═══════════════════════════════════════════════════════════════════════
# 顶层协议（标记接口 + source_name）
# ═══════════════════════════════════════════════════════════════════════


@runtime_checkable
class DataSourceAPI(Protocol):
    """统一数据源 API 协议（顶层）

    所有数据源（TushareAPI / AdataAPI / PytdxAPI / WindAPI / ChoiceAPI...）
    都要实现这个 Protocol，提供 source_name 和 available_methods。
    """

    @property
    def source_name(self) -> str:
        """数据源名（Tushare / Adata-THS / Pytdx / Wind...）"""
        ...

    @property
    def available_methods(self) -> list[str]:
        """返回该数据源支持的方法名列表（启动期校验用）

        例：TushareAPI 返回 ["fetch_kline", "fetch_daily_basic", "fetch_income", ...]
        """
        ...


# ═══════════════════════════════════════════════════════════════════════
# 6 个细粒度业务协议（按业务切）
# ═══════════════════════════════════════════════════════════════════════


@runtime_checkable
class KlineAPI(Protocol):
    """日 K 线协议"""

    async def fetch_kline(self, symbol: str, days: int = 30) -> CallResult:
        """采集日 K 线，返回 KlineBO 列表（data 字段）"""
        ...


@runtime_checkable
class MinuteKlineAPI(Protocol):
    """分钟 K 线协议"""

    async def fetch_minute_klines(
        self,
        symbol: str,
        interval: str = "5min",
        count: int = 800,
    ) -> CallResult:
        """采集分钟 K 线，返回 MinuteKlineBO 列表（data 字段）"""
        ...


@runtime_checkable
class StockBasicAPI(Protocol):
    """股票基本信息协议"""

    async def fetch_stock_basic(self, list_status: str = "L") -> CallResult:
        """全量拉取 A 股股票基本信息，返回 StockInfoBO 列表（data 字段）"""
        ...


@runtime_checkable
class DailyBasicAPI(Protocol):
    """日频估值协议"""

    async def fetch_daily_basic(self, trade_date: str) -> CallResult:
        """拉取指定交易日的全市场日频估值指标，返回 FinDailyBasicBO 列表

        Args:
            trade_date: YYYYMMDD 格式日期
        """
        ...


@runtime_checkable
class FinReportAPI(Protocol):
    """财务报告协议"""

    async def fetch_income(
        self,
        ts_code: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> CallResult:
        """单只股票合并报表利润表，返回 FinReportBO 列表（data 字段）

        Args:
            ts_code: Tushare 代码，如 600519.SH
            start_date / end_date: 公告日范围 YYYYMMDD
        """
        ...


@runtime_checkable
class ConceptAPI(Protocol):
    """概念板块协议（adata · 同花顺实现）

    所有方法以同花顺指数编码 index_code（885xxx）定位概念。
    """

    async def fetch_concept_list(self) -> CallResult:
        """全部概念：data 为 ConceptListBO 列表"""
        ...

    async def fetch_constituents(self, index_code: str) -> CallResult:
        """概念 → 成分股 symbol 列表；data 为 list[str]"""
        ...

    async def fetch_concepts_by_stock(self, symbol: str) -> CallResult:
        """股票 → 所属概念：data 为 ConceptOfStockBO 列表"""
        ...

    async def fetch_index_daily(self, index_code: str) -> CallResult:
        """概念指数日 K 全部历史：data 为 ConceptIndexTHBO 列表"""
        ...

    async def fetch_current(self, index_code: str) -> CallResult:
        """概念实时行情：data 为 ConceptCurrentBO 或 None"""
        ...


# ═══════════════════════════════════════════════════════════════════════
# 错误分类
# ═══════════════════════════════════════════════════════════════════════


class DataSourceError(Exception):
    """数据源错误的基类"""


class RateLimitError(DataSourceError):
    """限频（调用方应等待后重试）"""


class AuthError(DataSourceError):
    """认证失败（token 无效 / 权限不足）"""


class NetworkError(DataSourceError):
    """网络错误（连接失败 / 超时）"""


__all__ = [
    "CallResult",
    "DataSourceAPI",
    "KlineAPI",
    "MinuteKlineAPI",
    "StockBasicAPI",
    "DailyBasicAPI",
    "FinReportAPI",
    "ConceptAPI",
    "DataSourceError",
    "RateLimitError",
    "AuthError",
    "NetworkError",
]
