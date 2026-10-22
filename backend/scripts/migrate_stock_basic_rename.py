"""raw_data 库迁移：fundamental_stock_info → fundamental_stock_basic

改动内容：
  1) 表 RENAME
  2) DROP COLUMN total_shares（备份到 backup_total_shares_* 后再删）
  3) 索引重命名为 ORM StockBasicDB.__table_args__ 期望的名字
  4) 唯一约束对齐 SQLAlchemy 默认命名（<table>_<col>_key）

用法：
    python3 scripts/migrate_stock_basic_rename.py            # dry-run，只打印 SQL
    python3 scripts/migrate_stock_basic_rename.py --apply    # 真执行
    python3 scripts/migrate_stock_basic_rename.py --apply --yes  # 跳过二次确认
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from shared.infrastructure.connection.db_factory import raw_async_engine

OLD_TABLE = "fundamental_stock_info"
NEW_TABLE = "fundamental_stock_basic"
DROP_COLUMN = "total_shares"
BACKUP_TABLE = "backup_fundamental_stock_info_total_shares"

# ORM 侧单列 index=True 会自动命名为 ix_<tablename>_<col>
SINGLE_COL_INDEXES = [
    ("ix_fundamental_stock_info_ts_code",       "ix_fundamental_stock_basic_ts_code"),
    ("ix_fundamental_stock_info_symbol",        "ix_fundamental_stock_basic_symbol"),
    ("ix_fundamental_stock_info_name",          "ix_fundamental_stock_basic_name"),
    ("ix_fundamental_stock_info_area",          "ix_fundamental_stock_basic_area"),
    ("ix_fundamental_stock_info_industry",      "ix_fundamental_stock_basic_industry"),
    ("ix_fundamental_stock_info_market",        "ix_fundamental_stock_basic_market"),
    ("ix_fundamental_stock_info_exchange",      "ix_fundamental_stock_basic_exchange"),
    ("ix_fundamental_stock_info_list_status",   "ix_fundamental_stock_basic_list_status"),
]

# ORM 侧 __table_args__ 显式命名（不带表名前缀）
COMPOSITE_INDEXES = [
    ("ix_fundamental_stock_info_industry_market", "ix_stock_basic_industry_market"),
    ("ix_fundamental_stock_info_exchange_status", "ix_stock_basic_exchange_status"),
]

# SQLAlchemy unique=True 不显式命名 -> PG 默认 <table>_<col>_key
OLD_UNIQUE = "uq_fundamental_stock_info_symbol"
NEW_UNIQUE = "fundamental_stock_basic_symbol_key"

# PG rename 表时 *_pkey 约束会自动改名，但底层索引名不跟
OLD_PKEY_INDEX = "fundamental_stock_info_pkey"
NEW_PKEY_INDEX = "fundamental_stock_basic_pkey"


async def table_exists(conn, name: str) -> bool:
    r = await conn.execute(
        text("SELECT 1 FROM pg_tables WHERE schemaname='public' AND tablename=:n"),
        {"n": name},
    )
    return r.scalar() is not None


async def column_exists(conn, table: str, col: str) -> bool:
    r = await conn.execute(
        text("SELECT 1 FROM information_schema.columns "
             "WHERE table_name=:t AND column_name=:c"),
        {"t": table, "c": col},
    )
    return r.scalar() is not None


async def index_exists(conn, name: str) -> bool:
    r = await conn.execute(
        text("SELECT 1 FROM pg_indexes WHERE schemaname='public' AND indexname=:n"),
        {"n": name},
    )
    return r.scalar() is not None


async def constraint_exists(conn, table: str, name: str) -> bool:
    r = await conn.execute(
        text("SELECT 1 FROM pg_constraint "
             "WHERE conrelid = to_regclass(:t) AND conname=:n"),
        {"t": table, "n": name},
    )
    return r.scalar() is not None


async def plan(conn) -> list[str]:
    """根据当前实际状态生成待执行 DDL 列表（幂等：已完成的步骤自动跳过）

    注意：所有「存在性」检查都针对 OLD_TABLE，因为此时 rename 尚未执行，
    用 NEW_TABLE 查会全部落空。
    """
    steps: list[str] = []

    old_exists = await table_exists(conn, OLD_TABLE)
    new_exists = await table_exists(conn, NEW_TABLE)

    if not old_exists and not new_exists:
        print("[skip] 两张表都不存在，无需迁移（create_all 会新建 fundamental_stock_basic）")
        return steps

    if not old_exists:
        # 上次已跑过 rename，这次只补后面还没做的步骤（幂等重入）
        print("[skip] 表已重命名，继续检查剩余索引/约束")
        has_col = False
    else:
        # 1) 先备份 total_shares（必须在 rename 之前，否则引不到旧表名）
        has_col = await column_exists(conn, OLD_TABLE, DROP_COLUMN)
        if has_col:
            steps.append(
                f'CREATE TABLE IF NOT EXISTS "{BACKUP_TABLE}" AS '
                f'SELECT symbol, {DROP_COLUMN} AS total_shares, now() AS backed_up_at '
                f'FROM "{OLD_TABLE}" WHERE {DROP_COLUMN} IS NOT NULL;'
            )
        else:
            print(f"[skip] {DROP_COLUMN} 列不存在")

        # 2) rename table
        steps.append(f'ALTER TABLE "{OLD_TABLE}" RENAME TO "{NEW_TABLE}";')

        # 3) drop total_shares（PG 的 ALTER TABLE RENAME TO 会自动把索引/约束
        #    绑到新表上，所以索引重命名放在后面）
        if has_col:
            steps.append(f'ALTER TABLE "{NEW_TABLE}" DROP COLUMN "{DROP_COLUMN}";')

    # 4) rename indexes
    for old_name, new_name in SINGLE_COL_INDEXES + COMPOSITE_INDEXES:
        if await index_exists(conn, old_name):
            steps.append(f'ALTER INDEX "{old_name}" RENAME TO "{new_name}";')
        else:
            print(f"[skip] 索引 {old_name} 不存在")

    # 5) rename unique constraint（PG 已自动跟表改名的就查不到旧名，这里只补漏）
    if await constraint_exists(conn, NEW_TABLE, OLD_UNIQUE):
        steps.append(
            f'ALTER TABLE "{NEW_TABLE}" RENAME CONSTRAINT "{OLD_UNIQUE}" TO "{NEW_UNIQUE}";'
        )
    else:
        print(f"[skip] 约束 {OLD_UNIQUE} 不存在")

    # 6) rename 主键索引：PG 会把 *_pkey 约束跟着表一起改名，
    #    但底层索引仍留旧名，这里补齐（DDL 里两者是同一对象，改名安全）
    if await index_exists(conn, OLD_PKEY_INDEX):
        steps.append(f'ALTER INDEX "{OLD_PKEY_INDEX}" RENAME TO "{NEW_PKEY_INDEX}";')

    return steps


async def run(apply: bool) -> None:
    async with raw_async_engine.connect() as conn:
        print("=" * 70)
        print("迁移前状态")
        print("=" * 70)
        r = await conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname='public' "
                 "AND tablename LIKE 'fundamental_stock_basic%' "
                 "OR tablename LIKE 'fundamental_stock_info%' ORDER BY tablename")
        )
        print(f"   相关表: {[x[0] for x in r] or '无'}")

        # total_shares 非空行数（决定备份是否有意义）
        if await table_exists(conn, OLD_TABLE):
            r = await conn.execute(
                text(f'SELECT COUNT(*), COUNT("{DROP_COLUMN}") FROM "{OLD_TABLE}"')
            )
            total, non_null = r.one()
            print(f"   {OLD_TABLE}: {total} 行，{DROP_COLUMN} 非空 {non_null} 行")
        elif await table_exists(conn, NEW_TABLE):
            r = await conn.execute(text(f'SELECT COUNT(*) FROM "{NEW_TABLE}"'))
            print(f"   {NEW_TABLE}: {r.scalar()} 行")

        print()
        print("=" * 70)
        print("待执行 DDL")
        print("=" * 70)
        steps = await plan(conn)
        if not steps:
            print("   （无）")
            return
        for i, sql in enumerate(steps, 1):
            print(f"   {i:>2}. {sql}")

        if not apply:
            print()
            print(">>> dry-run 模式，未执行。确认无误后加 --apply")
            return

        print()
        print("=" * 70)
        print("执行中（单事务）")
        print("=" * 70)
        # 前面的一堆 SELECT 已经 autobegin 了（SQLAlchemy 2.x 默认行为），
        # 先把这个只读事务收掉，才能再开一个干净的 DDL 事务
        await conn.rollback()
        async with conn.begin():
            for i, sql in enumerate(steps, 1):
                try:
                    await conn.execute(text(sql))
                    print(f"   [{i}/{len(steps)}] OK  {sql[:88]}")
                except ProgrammingError as exc:
                    print(f"   [{i}/{len(steps)}] 失败 {sql}")
                    print(f"        {exc.orig}")
                    raise

        print()
        print("=" * 70)
        print("迁移后校验")
        print("=" * 70)
        r = await conn.execute(
            text("SELECT column_name, data_type FROM information_schema.columns "
                 "WHERE table_name=:t ORDER BY ordinal_position"),
            {"t": NEW_TABLE},
        )
        print(f"   {NEW_TABLE} 列 ({len(r.fetchall())} 个):")
        r = await conn.execute(
            text("SELECT column_name FROM information_schema.columns "
                 "WHERE table_name=:t ORDER BY ordinal_position"),
            {"t": NEW_TABLE},
        )
        for (c,) in r:
            print(f"      - {c}")

        r = await conn.execute(
            text("SELECT indexname FROM pg_indexes "
                 "WHERE schemaname='public' AND tablename=:t ORDER BY indexname"),
            {"t": NEW_TABLE},
        )
        print(f"   索引 ({len(r.fetchall())} 个)")
        r = await conn.execute(
            text("SELECT indexname FROM pg_indexes "
                 "WHERE schemaname='public' AND tablename=:t ORDER BY indexname"),
            {"t": NEW_TABLE},
        )
        for (n,) in r:
            print(f"      - {n}")

        r = await conn.execute(text(f'SELECT COUNT(*) FROM "{NEW_TABLE}"'))
        print(f"   行数: {r.scalar()}")

        if await table_exists(conn, BACKUP_TABLE):
            r = await conn.execute(text(f'SELECT COUNT(*) FROM "{BACKUP_TABLE}"'))
            print(f"   备份表 {BACKUP_TABLE}: {r.scalar()} 行")

        print()
        print(">>> 迁移完成。重启后端服务让 ORM metadata 缓存刷新。")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真正执行（默认 dry-run）")
    ap.add_argument("--yes", action="store_true", help="跳过确认")
    args = ap.parse_args()

    if args.apply and not args.yes:
        ans = input("确认执行以上 DDL？(yes/N) ")
        if ans.strip().lower() != "yes":
            print("已取消")
            return

    import asyncio
    asyncio.run(run(args.apply))


if __name__ == "__main__":
    main()