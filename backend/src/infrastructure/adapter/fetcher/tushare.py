"""Tushare Pro 数据采集器（实现 KlineFetcher / StockBasicFetcher / DailyBasicFetcher / FinReportFetcher）

使用 tushare.pro_api() 拉取数据：
- 日线行情（daily）
- 股票基本信息（stock_basic）
- 日频估值指标（daily_basic）
- 利润表（income，按单只股票；income_vip 需 5000 积分，当前账号无权限）

环境变量:
- TUSHARE_TOKEN  (在 .env 中配置，Pydantic-Settings 读取)

模块结构（fetcher + parser + 工具函数共生）：
- 工具函数    symbol_to_ts_code / parse_list_date / dedupe_income / _is_rate_limit
- Parser      TushareKlineParser（tushare DataFrame → KlineBO）
- Fetcher     TushareFetcher（采集器主类）
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional

import pandas as pd

from application.port.collector_port import CollectParams, RateLimitError
from infrastructure.adapter.fetcher.base import BaseCollector
from route.dto.request.fin_daily_basic import FinDailyBasicBO
from route.dto.request.fin_report import FinReportBO
from route.dto.request.kline import KlineBO
from route.dto.request.stock_info import StockInfoBO

logger = logging.getLogger(__name__)

_INCOME_VALUE_FIELDS = (
    "basic_eps", "diluted_eps", "total_revenue", "revenue",
    "operate_profit", "total_profit", "n_income", "n_income_attr_p",
)
_INCOME_FIELDS = ",".join((
    "ts_code", "ann_date", "f_ann_date", "end_date", "report_type", "comp_type",
    *_INCOME_VALUE_FIELDS, "update_flag",
))
_INCOME_KEY = ["ts_code", "end_date", "report_type"]


def _is_rate_limit(e: Exception) -> bool:
    msg = str(e)
    return "每分钟" in msg or "最多访问" in msg or "频率" in msg


def dedupe_income(df: pd.DataFrame) -> pd.DataFrame:
    """同一报告期 Tushare 会返回更正前后多行：优先 update_flag=1，其次实际公告日、公告日最新"""
    if df.empty:
        return df
    ordered = df.assign(
        _flag=df["update_flag"].fillna("0").astype(str),
        _f_ann=df["f_ann_date"].fillna("").astype(str),
        _ann=df["ann_date"].fillna("").astype(str),
    ).sort_values(["_flag", "_f_ann", "_ann"], ascending=False)
    return (
        ordered.drop_duplicates(subset=_INCOME_KEY, keep="first")
        .drop(columns=["_flag", "_f_ann", "_ann"])
        .sort_values("end_date", ascending=False)
    )


# ═══════════════════════════════════════════════════════════════
# 工具函数：股票代码 → Tushare ts_code 转换 + 日期解析
# ═══════════════════════════════════════════════════════════════


def symbol_to_ts_code(symbol: str) -> str:
    """把 6 位股票代码转换为 Tushare ts_code。"""
    if not symbol or len(symbol) != 6 or not symbol.isdigit():
        raise ValueError(f"无效的股票代码: {symbol!r}，应为 6 位数字")

    prefix2 = symbol[:2]
    prefix3 = symbol[:3]

    # 北交所：老代码 83/87/43/82，2024 年起新代码段 920xxx
    if prefix2 in ("83", "87", "43", "82", "92"):
        return f"{symbol}.BJ"

    if prefix3 in ("600", "601", "603", "605", "688", "689"):
        return f"{symbol}.SH"

    return f"{symbol}.SZ"


def parse_list_date(s) -> Optional[date]:
    """YYYYMMDD 字符串 → date"""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return None
    s = str(s).strip()
    if not s or s == "0" or s == "00000000":
        return None
    try:
        return pd.to_datetime(s, format="%Y%m%d").date()
    except Exception:
        try:
            return pd.to_datetime(s).date()
        except Exception:
            return None


# ═══════════════════════════════════════════════════════════════
# Parser（数据源字段 → BO）
# ═══════════════════════════════════════════════════════════════


class TushareKlineParser:
    """Tushare K 线数据解析器：将 tushare `pro.daily()` 返回的 DataFrame 转换为 KlineBO 列表。

    Tushare 字段说明:
    - trade_date: YYYYMMDD 字符串
    - vol:        成交量（手）
    - amount:     成交额（千元），需 *1000 转换为元
    - pct_chg:    涨跌幅（%），保留 2 位小数
    """

    def parse(self, df: pd.DataFrame, symbol: str) -> list[KlineBO]:
        """解析 Tushare DataFrame → KlineBO 列表"""
        if df is None or df.empty:
            return []

        results = []
        for _, row in df.iterrows():
            try:
                kline = self._parse_row(row, symbol)
                if kline is not None:
                    results.append(kline)
            except (KeyError, ValueError, TypeError):
                continue
        return results

    def _parse_row(self, row: pd.Series, symbol: str) -> Optional[KlineBO]:
        trade_date = self._parse_date(row["trade_date"])
        if trade_date is None:
            return None

        # Tushare 的 amount 单位是「千元」→ 转为「元」
        amount_kilo = row.get("amount")
        amount_yuan = float(amount_kilo) * 1000.0 if pd.notna(amount_kilo) else 0.0

        volume_raw = row.get("vol")
        volume = int(volume_raw) if pd.notna(volume_raw) else 0

        pct_chg = row.get("pct_chg")
        change_pct: Optional[float] = (
            float(pct_chg) if pd.notna(pct_chg) else None
        )

        return KlineBO(
            symbol=symbol,
            name="",
            trade_date=trade_date,
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=volume,
            amount=amount_yuan,
            change_pct=change_pct,
        )

    @staticmethod
    def _parse_date(value) -> Optional[date]:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        s = str(value).strip()
        for fmt in ("%Y%m%d", "%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
        try:
            return pd.to_datetime(s).date()
        except Exception:
            return None


# ═══════════════════════════════════════════════════════════════
# Fetcher（采集器主类）
# ═══════════════════════════════════════════════════════════════


class TushareFetcher(BaseCollector):
    """Tushare 数据采集器"""

    SOURCE_NAME = "Tushare"

    def __init__(self, data_type: type = KlineBO):
        super().__init__()
        self._kline_type = data_type
        if data_type is not KlineBO:
            raise ValueError(
                f"TushareFetcher 仅支持 KlineBO，当前类型: {data_type.__name__}"
            )
        self._parser = TushareKlineParser()
        self._name_cache: dict[str, str] = {}

        # 延迟导入，避免未安装时影响 AKShare 路径
        import tushare as ts  # noqa: WPS433
        from infrastructure.config.settings import get_settings

        token = get_settings().TUSHARE_TOKEN
        if not token:
            raise RuntimeError(
                "TUSHARE_TOKEN 未配置，请在 .env 中设置"
            )
        ts.set_token(token)
        self._pro = ts.pro_api()

    # ── K线采集 ─────────────────────────────────────────────

    def _resolve_name(
        self,
        symbol: str,
        ts_code: str,
        prefetched: Optional[str] = None,
    ) -> str:
        """查询股票名称（按优先级：调用方注入 > 缓存 > 远端）

        Args:
            symbol: 6 位股票代码
            ts_code: Tushare ts_code
            prefetched: 调用方已拿到的 name（命中则直接返回，避免打 Tushare）
        """
        if prefetched:
            self._name_cache[symbol] = prefetched
            return prefetched
        if symbol in self._name_cache:
            return self._name_cache[symbol]
        try:
            df = self._pro.stock_basic(
                ts_code=ts_code,
                fields="ts_code,name",
            )
            if df is not None and not df.empty:
                name = str(df.iloc[0]["name"])
                self._name_cache[symbol] = name
                return name
        except Exception as e:
            self._log("warning", f"查询股票名称失败 {symbol}: {e}")
        return ""

    def fetch(self, params: CollectParams) -> list[KlineBO]:
        """K 线采集

        名称解析优先级（避免每次都打 Tushare stock_basic）：
        1. params.name（调用方已注入，例如从本地 stock_infos 查到）
        2. 缓存命中（_name_cache）
        3. 兜底：Tushare stock_basic 单条查询（首次采集某 symbol 时）
        """
        if not params.symbol:
            raise ValueError("采集 K 线需要提供 symbol")

        ts_code = symbol_to_ts_code(params.symbol)
        stock_name = self._resolve_name(params.symbol, ts_code, params.name)

        end_date = params.end_date or date.today()
        start_date = params.start_date or (end_date - timedelta(days=params.days))

        buf_start = start_date - timedelta(days=2)
        start_str = buf_start.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")

        self._log("info", f"开始采集: {params.symbol} ({ts_code}) {buf_start}→{end_date}")

        try:
            df = self._pro.daily(
                ts_code=ts_code,
                start_date=start_str,
                end_date=end_str,
            )
        except Exception as e:
            raise self._wrap_error(f"调用 Tushare daily() 失败", e)

        if df is None or df.empty:
            self._log("warning", f"{params.symbol}: Tushare 返回空数据")
            return []

        df = df.sort_values("trade_date").reset_index(drop=True)
        klines = self._parser.parse(df, params.symbol)

        if stock_name:
            for k in klines:
                k.name = stock_name

        self._log(
            "info",
            f"采集完成: {params.symbol}, 获取 {len(klines)} 条, name={stock_name!r}",
        )
        return klines

    # ── 股票基本信息采集 ────────────────────────────────────

    def fetch_stock_basic(self, params: CollectParams) -> list[StockInfoBO]:
        """全量拉取 A 股股票基本信息

        Args:
            params.list_status: L=上市, D=退市, P=暂停上市, 默认 L
        """
        list_status = (params.list_status or "L").upper()
        self._log("info", f"开始拉取 stock_basic: list_status={list_status}")

        all_stocks: list[StockInfoBO] = []
        # Tushare 单次最多 6000 条，A 股 ~5400 条，一次取完即可
        # 但为稳妥起见，按交易所分批
        exchanges = ["SSE", "SZSE", "BSE"]

        for ex in exchanges:
            try:
                df = self._pro.stock_basic(
                    exchange=ex,
                    list_status=list_status,
                    fields="ts_code,symbol,name,area,industry,market,exchange,list_date,delist_date,list_status,is_hs,act_name,act_ent_type",
                )
            except Exception as e:
                self._log("warning", f"拉取 {ex} stock_basic 失败: {e}")
                continue

            if df is None or df.empty:
                self._log("info", f"{ex}: 无数据")
                continue

            for _, row in df.iterrows():
                try:
                    bo = self._row_to_stock_info_bo(row)
                    if bo:
                        all_stocks.append(bo)
                except Exception as e:
                    logger.warning("跳过无效行: %s", e)
                    continue

        self._log("info", f"stock_basic 同步完成，共 {len(all_stocks)} 条")
        return all_stocks

    # ── 日频估值指标采集 ────────────────────────────────────

    def fetch_daily_basic(self, trade_date: str) -> list[FinDailyBasicBO]:
        """拉取指定日期的全市场日频估值指标

        Args:
            trade_date: YYYYMMDD 格式的交易日期
        Returns:
            FinDailyBasicBO 列表
        """
        self._log("info", f"开始拉取 daily_basic: trade_date={trade_date}")

        try:
            df = self._pro.daily_basic(
                trade_date=trade_date,
                fields="ts_code,trade_date,close,turnover_rate,turnover_rate_f,"
                       "volume_ratio,pe,pe_ttm,pb,ps,ps_ttm,"
                       "dv_ratio,dv_ttm,total_share,float_share,free_share,"
                       "total_mv,circ_mv",
            )
        except Exception as e:
            self._log("warning", f"拉取 daily_basic 失败: {e}")
            return []

        if df is None or df.empty:
            self._log("info", f"daily_basic {trade_date}: 无数据")
            return []

        items: list[FinDailyBasicBO] = []
        for _, row in df.iterrows():
            try:
                bo = self._row_to_daily_basic_bo(row)
                if bo:
                    items.append(bo)
            except Exception as e:
                logger.warning("跳过无效 daily_basic 行: %s", e)

        self._log("info", f"daily_basic {trade_date} 完成，共 {len(items)} 条")
        return items

    @staticmethod
    def _row_to_daily_basic_bo(row: pd.Series) -> Optional[FinDailyBasicBO]:
        """DataFrame 行 → FinDailyBasicBO"""
        ts_code = row.get("ts_code")
        if not ts_code or pd.isna(ts_code):
            return None
        symbol = str(ts_code).split(".")[0]
        trade_date_val = row.get("trade_date")
        if not trade_date_val or pd.isna(trade_date_val):
            return None
        td = pd.to_datetime(str(trade_date_val), format="%Y%m%d").date()

        def _float(key: str) -> Optional[float]:
            v = row.get(key)
            if v is None or pd.isna(v):
                return None
            return float(v)

        return FinDailyBasicBO(
            symbol=symbol,
            trade_date=td,
            close=_float("close"),
            turnover_rate=_float("turnover_rate"),
            turnover_rate_f=_float("turnover_rate_f"),
            volume_ratio=_float("volume_ratio"),
            pe=_float("pe"),
            pe_ttm=_float("pe_ttm"),
            pb=_float("pb"),
            ps=_float("ps"),
            ps_ttm=_float("ps_ttm"),
            dv_ratio=_float("dv_ratio"),
            dv_ttm=_float("dv_ttm"),
            total_share=_float("total_share"),
            float_share=_float("float_share"),
            free_share=_float("free_share"),
            total_mv=_float("total_mv"),
            circ_mv=_float("circ_mv"),
        )

    # ── 利润表采集 ──────────────────────────────────────────

    def fetch_income(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list[FinReportBO]:
        """单只股票合并报表（report_type=1）利润表，按报告期去重

        异常上抛（限频转为 RateLimitError），由任务层记失败 / 重试。
        """
        kwargs = {"ts_code": ts_code, "report_type": "1", "fields": _INCOME_FIELDS}
        if start_date:
            kwargs["start_date"] = start_date
        if end_date:
            kwargs["end_date"] = end_date
        try:
            df = self._pro.income(**kwargs)
        except Exception as e:
            if _is_rate_limit(e):
                raise RateLimitError(str(e)) from e
            raise self._wrap_error(f"income {ts_code} 失败: {e}", e)

        if df is None or df.empty:
            return []
        items: list[FinReportBO] = []
        for _, row in dedupe_income(df).iterrows():
            bo = self._row_to_fin_report_bo(row)
            if bo:
                items.append(bo)
        return items

    @staticmethod
    def _row_to_fin_report_bo(row: pd.Series) -> Optional[FinReportBO]:
        """DataFrame 行 → FinReportBO"""
        ts_code = row.get("ts_code")
        end_date = parse_list_date(row.get("end_date"))
        if not ts_code or pd.isna(ts_code) or end_date is None:
            return None

        def _float(key: str) -> Optional[float]:
            v = row.get(key)
            if v is None or pd.isna(v):
                return None
            return float(v)

        def _str(key: str) -> Optional[str]:
            v = row.get(key)
            if v is None or pd.isna(v):
                return None
            return str(v)

        return FinReportBO(
            symbol=str(ts_code).split(".")[0],
            end_date=end_date,
            ann_date=parse_list_date(row.get("ann_date")),
            report_type=_str("report_type"),
            comp_type=_str("comp_type"),
            **{f: _float(f) for f in _INCOME_VALUE_FIELDS},
        )

    @staticmethod
    def _row_to_stock_info_bo(row: pd.Series) -> Optional[StockInfoBO]:
        """DataFrame 行 → StockInfoBO"""
        symbol = row.get("symbol")
        if not symbol or pd.isna(symbol):
            return None
        return StockInfoBO(
            symbol=str(symbol).zfill(6),
            ts_code=row.get("ts_code") or None,
            name=str(row.get("name") or ""),
            area=row.get("area") or None,
            industry=row.get("industry") or None,
            market=row.get("market") or None,
            exchange=row.get("exchange") or None,
            list_date=parse_list_date(row.get("list_date")),
            delist_date=parse_list_date(row.get("delist_date")),
            list_status=str(row.get("list_status") or "L"),
            is_hs=str(row.get("is_hs") or "N"),
            act_name=row.get("act_name") if pd.notna(row.get("act_name")) else None,
            act_ent_type=row.get("act_ent_type") if pd.notna(row.get("act_ent_type")) else None,
        )