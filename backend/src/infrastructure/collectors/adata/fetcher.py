"""adata 概念板块采集器（THS 同源反查，2026-09-27 09concept 重构）

历史背景：
- 原 adata 走 EM (datacenter.eastmoney.com) 链路；
  `get_concept_east(stock_code)` 可用，但与 akshare THS 清单「白酒 vs 白酒概念」类名错位。
- 2026-09-27 09concept 重构：改用 adata.stock.info.get_concept_ths(stock_code=...)
  走 THS 同源（q.10jqka.com.cn 后端），返回的概念名与 akshare THS 清单 100% 匹配。

当前能力矩阵（仅保留本期有用端点）：
- fetch_concepts_by_stock    ✅ THS 同源按股票反查 + 入选理由（独家）
- fetch_concept_list          ❌ 已废弃（akshare THS 清单更权威）
- fetch_concept_stocks        ❌ 已废弃（akshare THS 无 cons 端点）

网络诊断（2026-09-27）：
- q.10jqka.com.cn         ✅ 200（同花顺源）
- datacenter.eastmoney.com ✅ 200（仅保留兼容路径，已不用）
- push2.eastmoney.com      ❌ RST（akshare EM 全挂，本采集器不依赖）

配套设计文档：docs/dev/09concept/02-class-design.md §1
"""

from __future__ import annotations

import logging
import time

import pandas as pd

from domain.concept.entity import ConceptSource
from domain.concept.schemas import ConceptListBO
from infrastructure.collectors.base import BaseCollector
from infrastructure.collectors.protocols import ConceptFetcher

logger = logging.getLogger(__name__)


class AdataConceptFetcher(BaseCollector):
    """adata THS 同源概念采集器（实现 ConceptFetcher 协议）"""

    SOURCE_NAME = "Adata-THS"
    RETRY_TIMES = 2
    RETRY_DELAY = 1.0
    REQUEST_DELAY = 0.3

    def __init__(self):
        super().__init__()
        self._adata = self._ensure_adata()

    def _ensure_adata(self):
        try:
            import adata
            return adata
        except ImportError:
            raise RuntimeError("adata 未安装：pip install adata>=2.9.0")

    # ── 采集：核心能力（THS 同源反查）──────────────────────

    def fetch_concepts_by_stock(self, symbol: str) -> list[ConceptListBO]:
        """按股票代码反查所属概念（adata THS 同源，独家）

        实现：adata.stock.info.get_concept_ths(stock_code=symbol)
        返回字段：stock_code / concept_code / name / source / reason

        数据源与 akshare THS 清单同源（q.10jqka.com.cn），
        概念名 100% 匹配 THS 清单。
        """
        if not symbol or len(symbol) != 6 or not symbol.isdigit():
            logger.warning("Adata-THS: 无效 symbol: %s", symbol)
            return []

        logger.debug("Adata-THS: 反查股票 %s 的概念", symbol)

        try:
            df = self._fetch_with_retry(
                lambda: self._adata.stock.info.get_concept_ths(stock_code=symbol)
            )
        except Exception as e:
            logger.warning("Adata-THS 反查 %s 失败: %s", symbol, str(e)[:200])
            return []

        if df is None or df.empty:
            return []

        return self._parse_concepts_by_stock(df)

    # ── 协议兜底（不实现）────────────────────────────────

    def fetch_concept_list(self) -> list[ConceptListBO]:
        """已废弃：本能力由 AkShareConceptFetcher.fetch_concept_list（THS）覆盖"""
        logger.debug("Adata-THS: fetch_concept_list 已废弃，请用 AkShareFetcher")
        return []

    def fetch_concept_stocks(self, concept_name: str) -> list:
        """已废弃：akshare THS 无 cons 端点，adata constituent_ths 暂未实测"""
        logger.debug("Adata-THS: fetch_concept_stocks 已废弃")
        return []

    # ── 解析 ─────────────────────────────────────────

    @staticmethod
    def _parse_concepts_by_stock(df: pd.DataFrame) -> list[ConceptListBO]:
        """解析 adata.get_concept_ths 结果

        字段：stock_code / concept_code / name / source / reason
        """
        items = []
        for _, row in df.iterrows():
            try:
                name = str(row.get("name", "")).strip()
                if not name:
                    continue
                code = str(row.get("concept_code", "")).strip()
                reason = row.get("reason")
                reason_str = (
                    str(reason).strip()
                    if reason is not None and pd.notna(reason) and str(reason).strip()
                    else None
                )
                items.append(ConceptListBO(
                    name=name,
                    code=code,
                    source=ConceptSource.THS,  # ⭐ 09concept 关键变更：来源标记为 THS
                    stock_count=0,
                    reason=reason_str,
                ))
            except Exception as e:
                logger.debug("跳过无效行: %s", e)
                continue
        return items

    # ── 辅助 ─────────────────────────────────────────

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
AdataConceptFetcher.__implements_protocol__ = ConceptFetcher
