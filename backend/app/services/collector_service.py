"""数据采集服务（AkShare）"""

import asyncio
from datetime import date, timedelta
from typing import List, Optional

import akshare as ak
import pandas as pd
from sqlalchemy.orm import Session

from app.models.kline import KLine
from app.config import settings


class CollectorService:
    """数据采集服务 - 基于 AkShare"""

    def __init__(self, db: Session):
        self.db = db

    async def collect_klines(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        adjust: str = "qfq",
    ) -> int:
        """
        采集指定股票指定日期范围的K线数据

        Args:
            symbol: 股票代码，如 "600519"
            start_date: 开始日期
            end_date: 结束日期
            adjust: 复权类型 qfq=前复权, hfq=后复权

        Returns:
            采集的数据条数
        """
        try:
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(
                None,
                lambda: ak.stock_zh_a_hist(
                    symbol=symbol,
                    period="daily",
                    start_date=start_date.strftime("%Y%m%d"),
                    end_date=end_date.strftime("%Y%m%d"),
                    adjust=adjust,
                ),
            )

            klines = self._convert_to_klines(df)

            if klines:
                self._bulk_insert(klines)
                print(f"✅ 采集 {symbol} K线 {len(klines)} 条")
            else:
                print(f"⚠️ {symbol} 无数据")

            return len(klines)

        except Exception as e:
            print(f"❌ 采集 {symbol} 失败: {e}")
            return 0

    async def collect_klines_batch(
        self,
        symbols: List[str],
        start_date: date,
        end_date: date,
        delay: float = 1.0,
    ) -> dict:
        """
        批量采集多只股票K线

        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            delay: 请求间隔（秒）

        Returns:
            采集结果统计
        """
        results = {"success": 0, "failed": 0, "total": 0}

        for symbol in symbols:
            count = await self.collect_klines(symbol, start_date, end_date)
            if count > 0:
                results["success"] += 1
            else:
                results["failed"] += 1
            results["total"] += count

            if delay > 0:
                await asyncio.sleep(delay)

        return results

    async def get_stock_list(self, market: str = "A股") -> List[str]:
        """获取股票代码列表"""
        try:
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(
                None,
                lambda: ak.stock_info_a_code_name(),
            )
            return df["code"].tolist()
        except Exception as e:
            print(f"❌ 获取股票列表失败: {e}")
            return []

    async def collect_news(self, symbol: str, days: int = 7) -> int:
        """采集指定股票的新闻"""
        try:
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(
                None,
                lambda: ak.stock_news_em(symbol=symbol),
            )
            print(f"✅ 采集 {symbol} 新闻 {len(df)} 条")
            return len(df)
        except Exception as e:
            print(f"❌ 采集 {symbol} 新闻失败: {e}")
            return 0

    def _convert_to_klines(self, df: pd.DataFrame) -> List[KLine]:
        """将 DataFrame 转换为 KLine 模型列表"""
        klines = []

        for _, row in df.iterrows():
            try:
                kline = KLine(
                    code=str(row["股票代码"]),
                    name=str(row["名称"]),
                    date=pd.to_datetime(row["日期"]).date(),
                    open=float(row["开盘"]),
                    high=float(row["最高"]),
                    low=float(row["最低"]),
                    close=float(row["收盘"]),
                    volume=float(row["成交量"]),
                    amount=float(row["成交额"]),
                    change_pct=float(row["涨跌幅"]) if pd.notna(row.get("涨跌幅")) else None,
                    turnover_rate=float(row["换手率"]) if pd.notna(row.get("换手率")) else None,
                )
                klines.append(kline)
            except Exception as e:
                print(f"⚠️ 数据转换错误: {e}")
                continue

        return klines

    def _bulk_insert(self, klines: List[KLine]) -> None:
        """批量插入K线（存在则更新）"""
        for kline in klines:
            existing = (
                self.db.query(KLine)
                .filter(
                    KLine.code == kline.code,
                    KLine.date == kline.date,
                )
                .first()
            )

            if existing:
                # 更新
                existing.open = kline.open
                existing.high = kline.high
                existing.low = kline.low
                existing.close = kline.close
                existing.volume = kline.volume
                existing.amount = kline.amount
                existing.change_pct = kline.change_pct
                existing.turnover_rate = kline.turnover_rate
            else:
                # 新增
                self.db.add(kline)

        self.db.commit()
