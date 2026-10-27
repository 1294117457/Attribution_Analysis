"""attribution 库迁移：collect_logs 通用化（facet→category / kind→action / params→meta）

背景（2026-10-26）：
    collect_logs 原先是「采集日志专用表」，字段名带采集语义。
    现抽象为**通用操作日志表**（配套 shared/infrastructure/log_util.py）：

        facet  → category   分组维度（采集时 tech/capital/fundamental/...）
        kind   → action     动作类型（采集时 incremental/full_refresh/realtime）
        params → meta       动态上下文 JSONB（采集时存原始入参）
        (新增) duration_ms   耗时（毫秒）

    ★ RENAME COLUMN 只改列名、保留数据，不丢值。
    ★ 计数/进度（saved_count / fail_count / total_count / progress）保持标量，
      不塞进 JSONB —— 前端强依赖这几个字段。

同时处理：
    - status 默认值 pending → init（对齐 ORM default="init"）
    - 补齐 ORM 期望的索引（已存在则跳过）

用法：
    python3 scripts/migrate_collect_logs_generalize.py            # dry-run，只打印 DDL
    python3 scripts/migrate_collect_logs_generalize.py --apply    # 真执行
    python3 scripts/migrate_collect_logs_generalize.py --apply --yes  # 跳过二次确认
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from shared.infrastructure.connection.db_factory import db_async_engine

TABLE = "collect_logs"

# (旧列名, 新列名)
COLUMN_RENAMES = [
    ("facet", "category"),
    ("kind", "action"),
    ("params", "meta"),
]

# ORM __table_args__ 里显式声明的索引名
ORM_INDEXES = [
    "idx_collect_logs_service_name",
    "idx_collect_logs_status",
    "idx_collect_logs_started_at",
    "idx_collect_logs_service_time",
]


async def table_exists(conn, name: str) -> bool:
    r = await conn.execute(
        text("SELECT 1 FROM pg_tables WHERE schemaname='public' AND tablename=:n"),
        {"n": name},
    )
    return r.scalar() is not None


async def column_exists(conn, table: str, col: str) -> bool:
    r = await conn.execute(
        text("SELECT 1 FROM information_schema.columns "
             "WHERE table_schema='public' AND table_name=:t AND column_name=:c"),
        {"t": table, "c": col},
    )
    return r.scalar() is not None


async def index_exists(conn, name: str) -> bool:
    r = await conn.execute(
        text("SELECT 1 FROM pg_indexes WHERE schemaname='public' AND indexname=:n"),
        {"n": name},
    )
    return r.scalar() is not None


async def column_default(conn, table: str, col: str) -> str | None:
    r = await conn.execute(
        text("SELECT column_default FROM information_schema.columns "
             "WHERE table_schema='public' AND table_name=:t AND column_name=:c"),
        {"t": table, "c": col},
    )
    row = r.scalar()
    return row


async def plan(conn) -> list[str]:
    """根据当前实际状态生成待执行 DDL（幂等：已完成的自动跳过）"""
    steps: list[str] = []

    if not await table_exists(conn, TABLE):
        print("[skip] collect_logs 表不存在 —— 无需迁移"
              "（create_all 会按新 ORM 建出完整表）")
        return steps

    # 1) 列重命名
    for old, new in COLUMN_RENAMES:
        has_old = await column_exists(conn, TABLE, old)
        has_new = await column_exists(conn, TABLE, new)
        if has_old and has_new:
            print(f"[skip] {old} 和 {new} 同时存在 —— 需人工确认")
        elif has_old:
            steps.append(f'ALTER TABLE "{TABLE}" RENAME COLUMN "{old}" TO "{new}";')
        elif has_new:
            print(f"[skip] {old} → {new} 已完成")
        else:
            print(f"[skip] {old} / {new} 都不存在")

    # 2) 补 duration_ms（通用耗时字段）
    if not await column_exists(conn, TABLE, "duration_ms"):
        steps.append(f'ALTER TABLE "{TABLE}" ADD COLUMN "duration_ms" INTEGER;')
    else:
        print("[skip] duration_ms 已存在")

    # 3) status 默认值对齐 ORM（init）
    #    ⚠️ 只改默认值，不动历史行的 status 值
    default = await column_default(conn, TABLE, "status")
    if default and "init" not in default:
        steps.append(f'ALTER TABLE "{TABLE}" ALTER COLUMN "status" SET DEFAULT \'init\';')
    elif default is None:
        print("[skip] status 无默认值（NOT NULL 列由应用层负责）")
    else:
        print("[skip] status 默认值已是 init")

    # 4) 补齐 ORM 期望的索引
    for name in ORM_INDEXES:
        if not await index_exists(conn, name):
            if name == "idx_collect_logs_service_name":
                ddl = (f'CREATE INDEX IF NOT EXISTS "{name}" '
                       f'ON public."{TABLE}" (service_name);')
            elif name == "idx_collect_logs_status":
                ddl = (f'CREATE INDEX IF NOT EXISTS "{name}" '
                       f'ON public."{TABLE}" (status);')
            elif name == "idx_collect_logs_started_at":
                ddl = (f'CREATE INDEX IF NOT EXISTS "{name}" '
                       f'ON public."{TABLE}" (started_at DESC);')
            else:  # idx_collect_logs_service_time
                ddl = (f'CREATE INDEX IF NOT EXISTS "{name}" '
                       f'ON public."{TABLE}" (service_name, started_at DESC);')
            steps.append(ddl)
        else:
            print(f"[skip] 索引 {name} 已存在")

    return steps


async def run(apply: bool) -> None:
    async with db_async_engine.connect() as conn:
        print("=" * 70)
        print("迁移前状态")
        print("=" * 70)
        r = await conn.execute(text("SELECT current_database(), current_user"))
        db, user = r.one()
        print(f"   库: {db} | 用户: {user}")

        if await table_exists(conn, TABLE):
            r = await conn.execute(text(f'SELECT COUNT(*) FROM "{TABLE}"'))
            print(f"   {TABLE}: {r.scalar()} 行")
            r = await conn.execute(
                text("SELECT status, count(*) FROM collect_logs "
                     "GROUP BY status ORDER BY 2 DESC")
            )
            dist = ", ".join(f"{s}={c}" for s, c in r.all())
            print(f"   status 分布: {dist or '(空表)'}")

            print("\n   当前列:")
            r = await conn.execute(
                text("SELECT column_name FROM information_schema.columns "
                     "WHERE table_schema='public' AND table_name='collect_logs' "
                     "ORDER BY ordinal_position")
            )
            for (c,) in r:
                print(f"      - {c}")

        print()
        print("=" * 70)
        print("待执行 DDL")
        print("=" * 70)
        steps = await plan(conn)
        if not steps:
            print("   （无）—— 已是最新状态")
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
        # 前面的一堆 SELECT 已 autobegin（SQLAlchemy 2.x 默认行为），
        # 先收掉这个只读事务，才能再开一个干净的 DDL 事务
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
            text("SELECT column_name FROM information_schema.columns "
                 "WHERE table_schema='public' AND table_name='collect_logs' "
                 "ORDER BY ordinal_position")
        )
        cols = [c for (c,) in r]
        print(f"   列 ({len(cols)} 个): {cols}")

        # ORM 期望列 vs 实际列
        from shared.infrastructure.persistence.models import CollectLogDB
        orm_cols = [c.name for c in CollectLogDB.__table__.columns]
        missing = [c for c in orm_cols if c not in cols]
        extra = [c for c in cols if c not in orm_cols]
        print(f"   ORM 期望 {len(orm_cols)} 列 | 实际 {len(cols)} 列")
        print(f"   ORM 有但 DB 缺: {missing or '无 [OK]'}")
        print(f"   DB 有但 ORM 无: {extra or '无 [OK]'}")

        r = await conn.execute(
            text("SELECT indexname FROM pg_indexes "
                 "WHERE schemaname='public' AND tablename='collect_logs' "
                 "ORDER BY indexname")
        )
        idx = [n for (n,) in r]
        print(f"   索引: {idx}")
        print(f"   ORM 索引齐备: {'[OK]' if all(i in idx for i in ORM_INDEXES) else '[缺失]'}")

        r = await conn.execute(text(f'SELECT COUNT(*) FROM "{TABLE}"'))
        print(f"   行数: {r.scalar()}（迁移前应一致）")

        # 抽样验证数据没丢
        r = await conn.execute(
            text(f'SELECT service_name, category, action, meta, status '
                 f'FROM "{TABLE}" ORDER BY created_at DESC LIMIT 3')
        )
        print("\n   最近 3 行（新列名读出）:")
        for row in r.all():
            print(f"      {row}")

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
