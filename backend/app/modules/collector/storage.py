"""
数据存储层。
封装 K 线数据的数据库操作。
"""

from typing import Optional
from datetime import date

from sqlalchemy import create_engine, text
from app.config import settings
from app.modules.collector.schemas import KLineRecord


class KLineStorage:
    """K线数据存储"""

    def __init__(self):
        self._engine = None

    @property
    def engine(self):
        if self._engine is None:
            self._engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
        return self._engine

    def save(self, klines: list[KLineRecord]) -> int:
        """批量保存 K 线数据（UPSERT）"""
        if not klines:
            return 0

        sql = text("""
            INSERT INTO klines (code, name, date, open, high, low, close, volume, amount, change_pct, turnover_rate)
            VALUES (:code, :name, :date, :open, :high, :low, :close, :volume, :amount, :change_pct, :turnover_rate)
            ON CONFLICT (code, date) DO UPDATE SET
                name = EXCLUDED.name,
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume,
                amount = EXCLUDED.amount,
                change_pct = EXCLUDED.change_pct,
                turnover_rate = EXCLUDED.turnover_rate
        """)

        with self.engine.connect() as conn:
            for kline in klines:
                conn.execute(sql, {
                    "code": kline.code,
                    "name": kline.name,
                    "date": kline.date,
                    "open": kline.open,
                    "high": kline.high,
                    "low": kline.low,
                    "close": kline.close,
                    "volume": kline.volume,
                    "amount": kline.amount,
                    "change_pct": kline.change_pct,
                    "turnover_rate": kline.turnover_rate,
                })
            conn.commit()

        return len(klines)

    def get_klines(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """查询 K 线数据"""
        conditions = ["code = :code"]
        params = {"code": code, "limit": limit, "offset": offset}

        if start_date:
            conditions.append("date >= :start_date")
            params["start_date"] = start_date
        if end_date:
            conditions.append("date <= :end_date")
            params["end_date"] = end_date

        where_clause = " AND ".join(conditions)

        sql = text(f"""
            SELECT id, code, name, date, open, high, low, close, volume, amount, change_pct, turnover_rate
            FROM klines
            WHERE {where_clause}
            ORDER BY date DESC
            LIMIT :limit OFFSET :offset
        """)

        with self.engine.connect() as conn:
            result = conn.execute(text(sql), params)
            rows = result.fetchall()

        return [
            {
                "id": row[0],
                "code": row[1],
                "name": row[2],
                "date": row[3],
                "open": row[4],
                "high": row[5],
                "low": row[6],
                "close": row[7],
                "volume": row[8],
                "amount": row[9],
                "change_pct": row[10],
                "turnover_rate": row[11],
            }
            for row in rows
        ]

    def get_recent_klines(self, code: str, days: int = 30) -> list[dict]:
        """获取最近 N 天的 K 线数据（用于计算指标）"""
        sql = """
            SELECT id, code, name, date, open, high, low, close, volume, amount, change_pct, turnover_rate
            FROM klines
            WHERE code = :code
            ORDER BY date DESC
            LIMIT :limit
        """

        with self.engine.connect() as conn:
            result = conn.execute(text(sql), {"code": code, "limit": days})
            rows = result.fetchall()

        return [
            {
                "id": row[0],
                "code": row[1],
                "name": row[2],
                "date": row[3],
                "open": row[4],
                "high": row[5],
                "low": row[6],
                "close": row[7],
                "volume": row[8],
                "amount": row[9],
                "change_pct": row[10],
                "turnover_rate": row[11],
            }
            for row in rows
        ]

    def get_latest_date(self, code: str) -> Optional[str]:
        """获取某只股票最新的 K 线日期"""
        sql = text("""
            SELECT MAX(date) FROM klines WHERE code = :code
        """)

        with self.engine.connect() as conn:
            result = conn.execute(text(sql), {"code": code})
            row = result.fetchone()

        if row and row[0]:
            return str(row[0])
        return None
