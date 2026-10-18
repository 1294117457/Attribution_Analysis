"""用 SQLAlchemy reflect 实际表，对比 ORM 类的列期望"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import text
from shared.infrastructure.persistence.connection import RawSessionLocal

# 强制 import 所有 raw ORM，让 Base.metadata 知道表结构
import contexts.market.infrastructure.persistence.models.stock_info
import contexts.market.infrastructure.persistence.models.fin_daily_basic
import contexts.market.infrastructure.persistence.models.fin_report
import contexts.market.infrastructure.persistence.models.fin_top10_holders
import contexts.market.infrastructure.persistence.models.fin_top10_float
import contexts.market.infrastructure.persistence.models.base_dividend
import contexts.market.infrastructure.persistence.models.mkt_index_member
import contexts.market.infrastructure.persistence.models.mkt_sector_daily
import contexts.market.infrastructure.persistence.models.mkt_market_daily
import contexts.market.infrastructure.persistence.models.tech_kline
import contexts.market.infrastructure.persistence.models.base_adj_factor
import contexts.market.infrastructure.persistence.models.base_name_change
import contexts.market.infrastructure.persistence.models.base_suspend
import contexts.market.infrastructure.persistence.models.mkt_calendar
import contexts.market.infrastructure.persistence.models.cap_moneyflow
import contexts.market.infrastructure.persistence.models.cap_margin_detail
import contexts.market.infrastructure.persistence.models.cap_margin
import contexts.market.infrastructure.persistence.models.cap_top_list
import contexts.market.infrastructure.persistence.models.cap_top_inst
import contexts.market.infrastructure.persistence.models.cap_block_trade
import contexts.market.infrastructure.persistence.models.cap_holder_num
import contexts.concept.infrastructure.persistence.models.concept

from shared.infrastructure.persistence.orm_base import RawBase


async def check():
    raw_metadata = RawBase.metadata
    async with RawSessionLocal() as s:
        for table in sorted(raw_metadata.sorted_tables, key=lambda t: t.name):
            result = await s.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_schema='public' AND table_name = :tn
                ORDER BY ordinal_position
            """), {"tn": table.name})
            actual_cols = [r[0] for r in result]
            expected_cols = [c.name for c in table.columns]
            missing = [c for c in expected_cols if c not in actual_cols]
            extra = [c for c in actual_cols if c not in expected_cols]
            if missing or extra:
                print(f"[ERR] {table.name}")
                if missing: print(f"   ORM 期望但库里缺: {missing}")
                if extra: print(f"   库里有但 ORM 不知道: {extra}")
            else:
                print(f"[OK ] {table.name}  ({len(expected_cols)} cols)")

asyncio.run(check())
