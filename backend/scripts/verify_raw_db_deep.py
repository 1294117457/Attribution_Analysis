"""深度对账：列名 + 数据类型"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import text
from shared.infrastructure.connection.db_factory import raw_async_engine
from shared.infrastructure.persistence.orm_base import RawBase

# import all
import contexts.market.infrastructure.persistence.models.stock_info  # noqa
import contexts.market.infrastructure.persistence.models.fin_daily_basic  # noqa
import contexts.market.infrastructure.persistence.models.fin_report  # noqa
import contexts.market.infrastructure.persistence.models.fin_top10_holders  # noqa
import contexts.market.infrastructure.persistence.models.fin_top10_float  # noqa
import contexts.market.infrastructure.persistence.models.base_dividend  # noqa
import contexts.market.infrastructure.persistence.models.mkt_index_member  # noqa
import contexts.market.infrastructure.persistence.models.mkt_sector_daily  # noqa
import contexts.market.infrastructure.persistence.models.mkt_market_daily  # noqa
import contexts.market.infrastructure.persistence.models.tech_kline  # noqa
import contexts.market.infrastructure.persistence.models.base_adj_factor  # noqa
import contexts.market.infrastructure.persistence.models.base_name_change  # noqa
import contexts.market.infrastructure.persistence.models.base_suspend  # noqa
import contexts.market.infrastructure.persistence.models.mkt_calendar  # noqa
import contexts.market.infrastructure.persistence.models.cap_moneyflow  # noqa
import contexts.market.infrastructure.persistence.models.cap_margin_detail  # noqa
import contexts.market.infrastructure.persistence.models.cap_margin  # noqa
import contexts.market.infrastructure.persistence.models.cap_top_list  # noqa
import contexts.market.infrastructure.persistence.models.cap_top_inst  # noqa
import contexts.market.infrastructure.persistence.models.cap_block_trade  # noqa
import contexts.market.infrastructure.persistence.models.cap_holder_num  # noqa
import contexts.concept.infrastructure.persistence.models.concept  # noqa
import contexts.collect.infrastructure.persistence.models.cap_moneyflow_hsgt  # noqa
import contexts.collect.infrastructure.persistence.models.cap_hsgt_top10  # noqa
import contexts.collect.infrastructure.persistence.models.capital_limit_list_d  # noqa
import contexts.collect.infrastructure.persistence.models.news_article  # noqa
import contexts.collect.infrastructure.persistence.models.fundamental_stock_concept  # noqa


def normalize_type(db_type: str) -> str:
    """把 PG 类型归一化为与 SQLAlchemy 一致的形式"""
    t = db_type.lower()
    # varchar / character varying 视为同一类
    if "character varying" in t or t.startswith("varchar"):
        return "varchar"
    if t in ("integer", "bigint", "smallint"):
        return t
    if t == "double precision":
        return "float"
    if t in ("timestamp without time zone", "timestamp with time zone"):
        return "datetime"
    if t == "date":
        return "date"
    if t == "text":
        return "text"
    if t == "boolean":
        return "boolean"
    if "[]" in t:
        return "array"
    if t.startswith("numeric"):
        return "numeric"
    return t


def sa_type_of(col) -> str:
    """从 SQLAlchemy Column 推断简化的类型名"""
    t = str(col.type).lower()
    if "varchar" in t or "character varying" in t:
        return "varchar"
    if "bigint" in t:
        return "bigint"
    if "smallint" in t:
        return "smallint"
    if "integer" in t or "int4" in t:
        return "integer"
    if "float" in t or "double" in t:
        return "float"
    if "datetime" in t or "timestamp" in t:
        return "datetime"
    if "date" in t:
        return "date"
    if "text" in t:
        return "text"
    if "boolean" in t or "bool" in t:
        return "boolean"
    if "array" in t or "[]" in t:
        return "array"
    return t


async def main():
    print("=" * 80)
    print("raw_data_db 深度对账: 列名 + 类型")
    print("=" * 80)

    err_count = 0
    async with raw_async_engine.begin() as conn:
        for table in sorted(RawBase.metadata.sorted_tables, key=lambda t: t.name):
            r = await conn.execute(text("""
                SELECT column_name, data_type, udt_name
                FROM information_schema.columns
                WHERE table_schema='public' AND table_name = :tn
                ORDER BY ordinal_position
            """), {"tn": table.name})
            db_cols = {row[0]: (row[1], row[2]) for row in r}

            errs = []
            for c in table.columns:
                if c.name not in db_cols:
                    errs.append(f"MISSING {c.name}")
                    continue
                db_type_raw, _ = db_cols[c.name]
                db_t = normalize_type(db_type_raw)
                sa_t = sa_type_of(c)
                if sa_t != db_t:
                    errs.append(f"TYPE {c.name}: ORM={sa_t} vs DB={db_t}({db_type_raw})")

            if errs:
                err_count += len(errs)
                print(f"  [ERR] {table.name}")
                for e in errs: print(f"         {e}")
            else:
                print(f"  [OK ] {table.name}  ({len(table.columns)} cols)")

    print(f"\n{'='*80}")
    if err_count == 0:
        print("✅ 全部 30 张表 列名+类型 完全对齐")
    else:
        print(f"❌ {err_count} 处问题")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
