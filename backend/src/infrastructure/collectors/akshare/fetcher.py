"""AKShare 概念板块采集器

数据源：
- 概念清单：ak.stock_board_concept_name_em()
- 概念成分股：ak.stock_board_concept_cons_em(symbol=概念名称)

同步策略：
- 全量同步：首次运行时一次性拉取全部概念 + 成分股
- 增量同步：每周重新拉取概念清单，对比新增/退出

配套设计文档：
  docs/dev/06gainian/02-infrastructure-design.md §4
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import pandas as pd

from domain.concept.schemas import ConceptListBO, ConceptStockBO
from infrastructure.collectors.protocols import ConceptFetcher

logger = logging.getLogger(__name__)


class AkShareConceptFetcher:
    """东方财富概念板块采集器（实现 ConceptFetcher 协议）"""

    RETRY_TIMES = 2
    RETRY_DELAY = 1.0   # 秒
    REQUEST_DELAY = 0.3  # 东方财富接口建议间隔

    def __init__(self):
        self._ak = self._ensure_ak()

    def _ensure_ak(self):
        """延迟导入 akshare"""
        try:
            import akshare as ak  # noqa: WPS433
            return ak
        except ImportError:
            raise RuntimeError(
                "AKShare 未安装：pip install akshare"
            )

    @property
    def source_name(self) -> str:
        return "AkShare"

    # ── 采集 ─────────────────────────────────────────

    def fetch_concept_list(self) -> list[ConceptListBO]:
        """获取全量概念清单"""
        logger.info("AKShare: 开始拉取概念清单")

        try:
            df = self._fetch_with_retry(
                lambda: self._ak.stock_board_concept_name_em()
            )
        except Exception as e:
            logger.error("拉取概念清单失败: %s", e)
            return []

        if df is None or df.empty:
            logger.warning("概念清单为空")
            return []

        return self._parse_list(df)

    def fetch_concept_stocks(self, concept_name: str) -> list[ConceptStockBO]:
        """获取指定概念的成分股"""
        logger.debug("AKShare: 拉取概念成分股: %s", concept_name)

        try:
            df = self._fetch_with_retry(
                lambda: self._ak.stock_board_concept_cons_em(symbol=concept_name)
            )
        except Exception as e:
            logger.warning("拉取概念 %s 成分股失败: %s", concept_name, e)
            return []

        if df is None or df.empty:
            return []

        return self._parse_stocks(df, concept_name)

    # ── 解析 ─────────────────────────────────────────

    @staticmethod
    def _parse_list(df: pd.DataFrame) -> list[ConceptListBO]:
        """解析概念清单 DataFrame"""
        # 东方财富字段：板块名称 / 板块代码 / 最新价 / 涨跌额 / 涨跌幅 /
        #               总市值 / 换手率 / 上涨家数 / 下跌家数 / 领涨股票
        items = []
        for _, row in df.iterrows():
            try:
                name = str(row.get("板块名称", "")).strip()
                if not name:
                    continue
                code = str(row.get("板块代码", "")).strip()
                # 上涨家数 + 下跌家数作为 stock_count 近似
                stock_count = (
                    int(row.get("上涨家数", 0) or 0)
                    + int(row.get("下跌家数", 0) or 0)
                )

                items.append(ConceptListBO(
                    name=name,
                    code=code,
                    stock_count=stock_count,
                ))
            except Exception as e:
                logger.debug("跳过无效行: %s", e)
                continue
        return items

    @staticmethod
    def _parse_stocks(df: pd.DataFrame, concept_name: str) -> list[ConceptStockBO]:
        """解析成分股 DataFrame"""
        # 东方财富字段：序号 / 代码 / 名称 / 最新价 / 涨跌幅 / ...
        items = []
        for _, row in df.iterrows():
            try:
                raw_symbol = str(row.get("代码", "")).strip()
                if not raw_symbol:
                    continue
                symbol = raw_symbol.zfill(6)
                if len(symbol) != 6:
                    continue
                name = str(row.get("名称", "")).strip()
                if not name:
                    continue

                items.append(ConceptStockBO(
                    symbol=symbol,
                    name=name,
                    rank=int(row.get("序号", 0)) if pd.notna(row.get("序号")) else None,
                ))
            except Exception as e:
                logger.debug("跳过无效行: %s", e)
                continue
        return items

    # ── 辅助 ─────────────────────────────────────────

    def _fetch_with_retry(self, fn, retries: int = RETRY_TIMES) -> pd.DataFrame:
        """带重试的采集"""
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
