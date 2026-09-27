"""AKShare 概念板块采集器（THS 链路，2026-09-27 09concept 重构）

数据源策略：
- THS（q.10jqka.com.cn）：本期唯一清单/行情/K线数据源
- push2.eastmoney.com 自 2026-09-26 起从开发机 RST（akshare EM 接口全挂），
  本采集器已彻底移除 EM 路径。

组件清单：
- fetch_concept_list              ✅ 全量概念清单（ak.stock_board_concept_name_ths）
- fetch_concept_info_ths(name)    ✅ 单概念行情快照（ak.stock_board_concept_info_ths）
- fetch_concept_index_ths(name)   ✅ 概念指数日 K（ak.stock_board_concept_index_ths）
- fetch_concept_stocks(name)      ❌ akshare THS 无成分股端点（adata 反查是唯一来源）
- fetch_concepts_by_stock(symbol) ❌ akshare 不支持（AdataConceptFetcher 独家）

配套设计文档：
  docs/dev/09concept/02-class-design.md §2
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import pandas as pd

from domain.concept.entity import ConceptSource
from domain.concept.schemas import (
    ConceptIndexTHBO,
    ConceptListBO,
    ConceptSnapshotBO,
    ConceptStockBO,
)
from infrastructure.collectors.base import BaseCollector
from infrastructure.collectors.protocols import ConceptFetcher

logger = logging.getLogger(__name__)


class AkShareConceptFetcher(BaseCollector):
    """AKShare THS 概念板块采集器（实现 ConceptFetcher 协议）"""

    SOURCE_NAME = "AkShare-THS"
    RETRY_TIMES = 2
    RETRY_DELAY = 1.0
    REQUEST_DELAY = 0.3

    def __init__(self):
        super().__init__()
        self._ak = self._ensure_ak()

    def _ensure_ak(self):
        try:
            import akshare as ak
            return ak
        except ImportError:
            raise RuntimeError("AKShare 未安装：pip install akshare")

    # ── 清单（唯一入口：THS）────────────────────────────────────

    def fetch_concept_list(self) -> list[ConceptListBO]:
        """全量概念清单（ak.stock_board_concept_name_ths）

        THS 接口字段：name / code（THS 内部编码，如 885525）
        375 个概念，覆盖绝大多数 A 股概念。
        """
        logger.info("AkShare-THS: 拉取概念清单")
        try:
            df = self._fetch_with_retry(
                lambda: self._ak.stock_board_concept_name_ths()
            )
        except Exception as e:
            logger.error("AkShare-THS: 清单接口失败: %s: %s", type(e).__name__, str(e)[:200])
            return []
        if df is None or df.empty:
            return []
        return self._parse_ths_list(df)

    # ── 行情快照（THS）────────────────────────────────────

    def fetch_concept_info_ths(self, concept_name: str) -> Optional[ConceptSnapshotBO]:
        """单概念行情快照（ak.stock_board_concept_info_ths）

        字段（实参实测）：
          板块名称 / 今开 / 昨收 / 最低 / 最高 / 成交量(万手) /
          板块涨幅 / 涨幅排名 / 涨跌家数 / 资金净流入(亿) / 成交额(亿)

        返回的 pct_change 是 "X.XX%" 字符串，本类不解析。
        """
        if not concept_name or not concept_name.strip():
            return None
        logger.debug("AkShare-THS: 拉取概念行情 %s", concept_name)
        try:
            df = self._fetch_with_retry(
                lambda: self._ak.stock_board_concept_info_ths(symbol=concept_name)
            )
        except Exception as e:
            logger.warning("AkShare-THS: %s 行情拉取失败: %s", concept_name, str(e)[:200])
            return None
        if df is None or df.empty:
            return None
        return self._parse_concept_info(df, concept_name)

    # ── 指数日 K（THS）────────────────────────────────────

    def fetch_concept_index_ths(
        self,
        concept_name: str,
        start_date: str = "20240101",
        end_date: str = "20991231",
    ) -> list[ConceptIndexTHBO]:
        """概念指数日 K（ak.stock_board_concept_index_ths）

        Args:
            concept_name: 概念名（THS 清单里的 name）
            start_date / end_date: YYYYMMDD 格式

        字段：日期 / 开盘价 / 最高价 / 最低价 / 收盘价 / 成交量 / 成交额
        """
        if not concept_name or not concept_name.strip():
            return []
        logger.debug(
            "AkShare-THS: 拉取 %s 指数日 K [%s, %s]",
            concept_name, start_date, end_date,
        )
        try:
            df = self._fetch_with_retry(
                lambda: self._ak.stock_board_concept_index_ths(
                    symbol=concept_name,
                    start_date=start_date,
                    end_date=end_date,
                )
            )
        except Exception as e:
            logger.warning(
                "AkShare-THS: %s 指数日 K 拉取失败: %s",
                concept_name, str(e)[:200],
            )
            return []
        if df is None or df.empty:
            return []
        return self._parse_concept_index(df, concept_name)

    # ── 不支持的能力（协议兜底）─────────────────────────────

    def fetch_concept_stocks(self, concept_name: str) -> list[ConceptStockBO]:
        """akshare THS 不提供「概念→成分股」端点

        唯一可行路径：AdataConceptFetcher.get_concept_ths(stock_code) 反查。
        本方法返回空 list 作为协议兜底。
        """
        logger.debug(
            "AkShare-THS: fetch_concept_stocks(%s) 不支持（akshare 无 THS cons 端点）",
            concept_name,
        )
        return []

    def fetch_concepts_by_stock(self, symbol: str) -> list[ConceptListBO]:
        """akshare 不支持「股票→概念」反查，由 AdataConceptFetcher 提供"""
        logger.debug(
            "AkShare-THS: fetch_concepts_by_stock(%s) 不支持，请使用 AdataFetcher",
            symbol,
        )
        return []

    # ── 解析 ─────────────────────────────────────────

    @staticmethod
    def _parse_ths_list(df: pd.DataFrame) -> list[ConceptListBO]:
        """解析 THS 概念清单 DataFrame（source=ths）

        THS 接口字段：name / code（同花顺内部编码）
        注：code 是 885xxx 系列，跟 akshare THS 清单 1:1 对应。
        """
        items = []
        for _, row in df.iterrows():
            try:
                name = str(row.get("name", "")).strip()
                if not name:
                    continue
                code = str(row.get("code", "")).strip()
                items.append(ConceptListBO(
                    name=name,
                    code=code,
                    source=ConceptSource.THS,
                    stock_count=0,
                ))
            except Exception as e:
                logger.debug("跳过无效行: %s", e)
                continue
        return items

    @staticmethod
    def _parse_concept_info(df: pd.DataFrame, concept_name: str) -> Optional[ConceptSnapshotBO]:
        """解析 THS 行情 DataFrame（单行）

        DataFrame 通常只有 1 行（某个概念当日的 1 行数据）。
        """
        if df.empty:
            return None
        row = df.iloc[0]
        try:
            def _s(col) -> Optional[str]:
                v = row.get(col)
                if v is None or (isinstance(v, float) and pd.isna(v)):
                    return None
                return str(v).strip() if not isinstance(v, (int, float)) else str(v)

            def _f(col) -> Optional[float]:
                v = row.get(col)
                if v is None or (isinstance(v, float) and pd.isna(v)):
                    return None
                try:
                    return float(v)
                except (TypeError, ValueError):
                    return None

            def _i(col) -> Optional[int]:
                v = row.get(col)
                if v is None or (isinstance(v, float) and pd.isna(v)):
                    return None
                try:
                    return int(v)
                except (TypeError, ValueError):
                    return None

            rank_label = _s("涨幅排名") or ""
            up_down_label = _s("涨跌家数") or ""

            return ConceptSnapshotBO(
                concept_name=str(row.get("板块名称") or concept_name).strip(),
                open_price=_f("今开"),
                prev_close=_f("昨收"),
                low=_f("最低"),
                high=_f("最高"),
                volume_wan=_f("成交量(万手)"),
                pct_change_raw=_s("板块涨幅") or "0.00%",
                rank_label=rank_label,
                up_down_label=up_down_label,
                net_inflow_yi=_f("资金净流入(亿)"),
                turnover_yi=_f("成交额(亿)"),
                rank_current=AkShareConceptFetcher._parse_rank_current(rank_label),
                rank_total=AkShareConceptFetcher._parse_rank_total(rank_label),
                up_count=AkShareConceptFetcher._parse_up_count(up_down_label),
                down_count=AkShareConceptFetcher._parse_down_count(up_down_label),
                source=ConceptSource.THS,
            )
        except Exception as e:
            logger.warning("解析概念行情失败 (%s): %s", concept_name, e)
            return None

    @staticmethod
    def _parse_concept_index(df: pd.DataFrame, concept_name: str) -> list[ConceptIndexTHBO]:
        """解析 THS 概念指数日 K

        字段：日期 / 开盘价 / 最高价 / 最低价 / 收盘价 / 成交量 / 成交额
        """
        from datetime import datetime, timezone
        items: list[ConceptIndexTHBO] = []
        now = datetime.now(timezone.utc)
        for _, row in df.iterrows():
            try:
                date_v = row.get("日期")
                if date_v is None or (isinstance(date_v, float) and pd.isna(date_v)):
                    continue
                # pandas.Timestamp / str 都支持
                if hasattr(date_v, "date"):
                    trade_date = date_v.date()
                else:
                    trade_date = datetime.strptime(str(date_v)[:10], "%Y-%m-%d").date()

                def _f(col) -> Optional[float]:
                    v = row.get(col)
                    if v is None or (isinstance(v, float) and pd.isna(v)):
                        return None
                    try:
                        return float(v)
                    except (TypeError, ValueError):
                        return None

                items.append(ConceptIndexTHBO(
                    concept_name=concept_name,
                    trade_date=trade_date,
                    open=_f("开盘价") or 0.0,
                    high=_f("最高价") or 0.0,
                    low=_f("最低价") or 0.0,
                    close=_f("收盘价") or 0.0,
                    volume=int(_f("成交量") or 0),
                    amount=_f("成交额") or 0.0,
                    source=ConceptSource.THS,
                    captured_at=now,
                ))
            except Exception as e:
                logger.debug("跳过无效日 K 行 (%s): %s", concept_name, e)
                continue
        return items

    # ── 辅助 ─────────────────────────────────────────

    @staticmethod
    def _parse_rank_current(label: str) -> Optional[int]:
        """'191/390' → 191"""
        if not label or "/" not in label:
            return None
        try:
            return int(label.split("/")[0])
        except (ValueError, IndexError):
            return None

    @staticmethod
    def _parse_rank_total(label: str) -> Optional[int]:
        """'191/390' → 390"""
        if not label or "/" not in label:
            return None
        try:
            return int(label.split("/")[1])
        except (ValueError, IndexError):
            return None

    @staticmethod
    def _parse_up_count(label: str) -> Optional[int]:
        """'90/372' → 90"""
        if not label or "/" not in label:
            return None
        try:
            return int(label.split("/")[0])
        except (ValueError, IndexError):
            return None

    @staticmethod
    def _parse_down_count(label: str) -> Optional[int]:
        """'90/372' → 372"""
        if not label or "/" not in label:
            return None
        try:
            return int(label.split("/")[1])
        except (ValueError, IndexError):
            return None

    def _fetch_with_retry(self, fn, retries: int = RETRY_TIMES):
        for i in range(retries + 1):
            try:
                time.sleep(self.REQUEST_DELAY)
                return fn()
            except Exception as e:
                if i < retries:
                    logger.debug("请求失败，重试 %d/%d: %s", i + 1, retries, e)
                    time.sleep(self.RETRY_DELAY)
                else:
                    raise


# ── Protocol 实现标注 ─────────────────────────────────
AkShareConceptFetcher.__implements_protocol__ = ConceptFetcher
