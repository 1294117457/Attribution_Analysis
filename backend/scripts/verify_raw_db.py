"""只跑对账，不改任何东西（用来诊断当前状态）

用法:
    cd backend
    python -m scripts.verify_raw_db
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import text
from shared.infrastructure.connection.db_factory import raw_async_engine
from shared.infrastructure.persistence.orm_base import RawBase

# import all raw ORM
import contexts.market.infrastructure.persistence.models.stock_info  # noqa: F401
import contexts.market.infrastructure.persistence.models.fin_daily_basic  # noqa: F401
import contexts.market.infrastructure.persistence.models.fin_report  # noqa: F401
import contexts.market.infrastructure.persistence.models.fin_top10_holders  # noqa: F401
import contexts.market.infrastructure.persistence.models.fin_top10_float  # noqa: F401
import contexts.market.infrastructure.persistence.models.base_dividend  # noqa: F401
import contexts.market.infrastructure.persistence.models.mkt_index_member  # noqa: F401
import contexts.market.infrastructure.persistence.models.mkt_sector_daily  # noqa: F401
import contexts.market.infrastructure.persistence.models.mkt_market_daily  # noqa: F401
import contexts.market.infrastructure.persistence.models.tech_kline  # noqa: F401
import contexts.market.infrastructure.persistence.models.base_adj_factor  # noqa: F401
import contexts.market.infrastructure.persistence.models.base_name_change  # noqa: F401
import contexts.market.infrastructure.persistence.models.base_suspend  # noqa: F401
import contexts.market.infrastructure.persistence.models.mkt_calendar  # noqa: F401
import contexts.market.infrastructure.persistence.models.cap_moneyflow  # noqa: F401
import contexts.market.infrastructure.persistence.models.cap_margin_detail  # noqa: F401
import contexts.market.infrastructure.persistence.models.cap_margin  # noqa: F401
import contexts.market.infrastructure.persistence.models.cap_top_list  # noqa: F401
import contexts.market.infrastructure.persistence.models.cap_top_inst  # noqa: F401
import contexts.market.infrastructure.persistence.models.cap_block_trade  # noqa: F401
import contexts.market.infrastructure.persistence.models.cap_holder_num  # noqa: F401
import contexts.concept.infrastructure.persistence.models.concept  # noqa: F401
import contexts.collect.infrastructure.persistence.models.cap_moneyflow_hsgt  # noqa: F401
import contexts.collect.infrastructure.persistence.models.cap_hsgt_top10  # noqa: F401
import contexts.collect.infrastructure.persistence.models.capital_limit_list_d  # noqa: F401
import contexts.collect.infrastructure.persistence.models.news_article  # noqa: F401
import contexts.collect.infrastructure.persistence.models.fundamental_stock_concept  # noqa: F401


async def main():
    print("=" * 70)
    print("raw_data_db ORM 期望 vs DB 实际 对账")
    print("=" * 70)

    async with raw_async_engine.begin() as conn:
        # 列出 DB 中所有表
        r = await conn.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema='public' AND table_type='BASE TABLE'
            ORDER BY table_name
        """))
        db_tables = [row[0] for row in r]
        print(f"\nDB 中现有 {len(db_tables)} 张表:")
        for t in db_tables: print(f"  - {t}")

        # 列出 ORM 声明的表
        orm_tables = [t.name for t in RawBase.metadata.sorted_tables]
        print(f"\nORM 声明 {len(orm_tables)} 张表:")
        for t in orm_tables: print(f"  - {t}")

        # ORM 声明但 DB 缺
        missing_in_db = [t for t in orm_tables if t not in db_tables]
        if missing_in_db:
            print(f"\n❌ ORM 声明但 DB 不存在（需 create_all）: {missing_in_db}")
        # DB 有但 ORM 不知道
        extra_in_db = [t for t in db_tables if t not in orm_tables]
        if extra_in_db:
            print(f"\n⚠️  DB 存在但 ORM 不知道: {extra_in_db}")

        print("\n逐表对账:")
        for table in sorted(RawBase.metadata.sorted_tables, key=lambda t: t.name):
            r = await conn.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_schema='public' AND table_name = :tn
                ORDER BY ordinal_position
            """), {"tn": table.name})
            actual = [row[0] for row in r]
            expected = [c.name for c in table.columns]
            missing = [c for c in expected if c not in actual]
            extra = [c for c in actual if c not in expected]
            if missing or extra:
                print(f"  [ERR] {table.name}  (实际 {len(actual)} / 期望 {len(expected)})")
                if missing: print(f"         缺: {missing}")
                if extra:   print(f"         多: {extra}")
            else:
                print(f"  [OK ] {table.name}  ({len(expected)} cols)")


if __name__ == "__main__":
    asyncio.run(main())
