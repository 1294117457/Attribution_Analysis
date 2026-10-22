"""迁移前探查：确认 raw_data 库里 fundamental_stock_info 的真实状态

只读，不做任何写操作。输出：
  1) 表是否存在（fundamental_stock_info / fundamental_stock_basic）
  2) 现有列清单 + total_shares 是否有值
  3) 索引 / 约束清单（含名字）
  4) 是否有外键指向该表
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import text
from shared.infrastructure.connection.db_factory import raw_async_engine

OLD = "fundamental_stock_info"
NEW = "fundamental_stock_basic"


async def probe():
    async with raw_async_engine.connect() as conn:
        print("=" * 70)
        print("1) 表存在性")
        print("=" * 70)
        r = await conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname='public' "
                 "AND tablename IN (:o, :n)"),
            {"o": OLD, "n": NEW},
        )
        rows = [x[0] for x in r]
        print(f"   {OLD}: {'存在' if OLD in rows else '不存在'}")
        print(f"   {NEW}: {'存在' if NEW in rows else '不存在'}")

        target = OLD if OLD in rows else (NEW if NEW in rows else None)
        if not target:
            print("\n两张表都不存在 -> 无需迁移，直接 create_all 即可")
            return
        print(f"\n   >>> 实际操作的表: {target}")

        print()
        print("=" * 70)
        print(f"2) {target} 列清单")
        print("=" * 70)
        r = await conn.execute(
            text("SELECT ordinal_position, column_name, data_type, is_nullable "
                 "FROM information_schema.columns "
                 "WHERE table_name = :t ORDER BY ordinal_position"),
            {"t": target},
        )
        for pos, col, dtype, nullable in r:
            flag = ""
            if col == "total_shares":
                flag = "  <-- 待删除"
            print(f"   {pos:>2}. {col:<20} {dtype:<28} null={nullable}{flag}")

        print()
        print("=" * 70)
        print(f"3) {target} 索引 / 约束")
        print("=" * 70)
        r = await conn.execute(
            text("SELECT indexname, indexdef FROM pg_indexes "
                 "WHERE schemaname='public' AND tablename = :t ORDER BY indexname"),
            {"t": target},
        )
        for name, ddl in r:
            print(f"   - {name}")
            print(f"       {ddl.split(' USING ')[-1]}")

        print()
        print("=" * 70)
        print(f"4) 指向 {target} 的外键")
        print("=" * 70)
        r = await conn.execute(
            text("SELECT conrelid::regclass::text AS tbl, conname, "
                 "pg_get_constraintdef(oid) AS def FROM pg_constraint "
                 "WHERE contype='f' AND pg_get_constraintdef(oid) LIKE :pat"),
            {"pat": f"%{target}%"},
        )
        fks = r.fetchall()
        if not fks:
            print("   无")
        for tbl, cname, d in fks:
            print(f"   {tbl} . {cname}")
            print(f"       {d}")

        print()
        print("=" * 70)
        print(f"5) {target} 行数")
        print("=" * 70)
        r = await conn.execute(text(f'SELECT COUNT(*) FROM "{target}"'))
        print(f"   {r.scalar()} 行")


asyncio.run(probe())