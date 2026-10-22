"""验证真实数据库表结构是否对得上 ORM 期望"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import text
from shared.infrastructure.connection.db_factory import db_session_factory, raw_session_factory


async def check():
    # raw_data 库
    async with raw_session_factory() as s:
        expected = [
            # tech_
            "tech_daily", "tech_adj_factor", "tech_namechange", "tech_suspend_d", "tech_trade_cal",
            # capital_
            "capital_moneyflow", "capital_margin_detail", "capital_margin", "capital_top_list",
            "capital_top_inst", "capital_block_trade", "capital_stk_holdernumber",
            "capital_moneyflow_hsgt", "capital_hsgt_top10", "capital_limit_list_d",
            # fundamental_（Tushare）
            "fundamental_daily_basic", "fundamental_income", "fundamental_top10_holders",
            "fundamental_top10_floatholders", "fundamental_dividend", "fundamental_index_member",
            "fundamental_sector_daily", "fundamental_index_daily", "fundamental_stock_basic",
            # fundamental_（adata 概念）
            "fundamental_concept", "fundamental_concept_member", "fundamental_concept_index",
            "fundamental_concept_snapshot", "fundamental_stock_concept",
            # news_
            "news_article",
        ]
        result = await s.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"))
        actual = [r[0] for r in result]
        ok = [t for t in expected if t in actual]
        miss = [t for t in expected if t not in actual]
        print(f"raw_data 库: 共 {len(actual)} 张表")
        print(f"  期望 {len(expected)} 张: 找到 {len(ok)}, 缺失 {len(miss)}")
        if miss:
            print(f"  缺失: {miss}")
        extra = [t for t in actual if t not in expected and not t.startswith("backup_")]
        if extra:
            print(f"  多余(未登记): {extra}")

    # attribution 库
    async with db_session_factory() as s:
        result = await s.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"))
        actual = [r[0] for r in result]
        print(f"\nattribution 库: 共 {len(actual)} 张表")
        for t in actual:
            print(f"  - {t}")


asyncio.run(check())
