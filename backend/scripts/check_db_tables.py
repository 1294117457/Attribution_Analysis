"""验证真实数据库表结构是否对得上 ORM 期望"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import text
from shared.infrastructure.persistence.connection import RawSessionLocal, AsyncSessionLocal


async def check():
    # raw_data 库
    async with RawSessionLocal() as s:
        expected = [
            "tech_kline_daily", "tech_adj_factor", "tech_name_change", "tech_suspend", "tech_calendar",
            "capital_moneyflow", "capital_margin_detail", "capital_margin", "capital_top_list",
            "capital_top_inst", "capital_block_trade", "capital_holder_num",
            "fundamental_daily_basic", "fundamental_report", "fundamental_top10", "fundamental_top10_float",
            "fundamental_dividend", "fundamental_index_member", "fundamental_sector_daily",
            "fundamental_market_daily", "fundamental_stock_info", "fundamental_concept",
            "fundamental_concept_member", "fundamental_concept_index", "fundamental_concept_snapshot",
        ]
        result = await s.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"))
        actual = [r[0] for r in result]
        ok = [t for t in expected if t in actual]
        miss = [t for t in expected if t not in actual]
        print(f"raw_data 库: 共 {len(actual)} 张表")
        print(f"  期望 25 张: 找到 {len(ok)}, 缺失 {len(miss)}")
        if miss:
            print(f"  缺失: {miss}")

    # attribution 库
    async with AsyncSessionLocal() as s:
        result = await s.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"))
        actual = [r[0] for r in result]
        print(f"\nattribution 库: 共 {len(actual)} 张表")
        for t in actual:
            print(f"  - {t}")


asyncio.run(check())
