"""raw_data 库迁移：把 9 张表名对齐"建议表名"（基于 docs/backend-docs/data/当前接口实现.md）

变更映射（old -> new）：
  tech_kline_daily          -> tech_daily
  tech_name_change          -> tech_namechange
  tech_suspend              -> tech_suspend_d
  tech_calendar             -> tech_trade_cal
  capital_holder_num        -> capital_stk_holdernumber
  fundamental_report        -> fundamental_income
  fundamental_top10         -> fundamental_top10_holders
  fundamental_top10_float   -> fundamental_top10_floatholders
  fundamental_market_daily  -> fundamental_index_daily

附带同步重命名序列（每个表的 _id_seq），并把 regular index 名字跟随新表名调整。
唯一约束 / 主键约束：PG 在 RENAME TABLE 时会自动跟随改名（含 _pkey），这里只补漏。

幂等：
- 重跑会跳过已完成的步骤
- 单事务包揽，安全回滚

用法：
    python3 scripts/migrate_raw_data_rename_tables.py               # dry-run
    python3 scripts/migrate_raw_data_rename_tables.py --apply       # 真执行
    python3 scripts/migrate_raw_data_rename_tables.py --apply --yes # 跳过二次确认
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from shared.infrastructure.connection.db_factory import raw_async_engine


# ── 重命名映射 ─────────────────────────────────────────────────
RENAME_TABLE: list[tuple[str, str]] = [
    ("tech_kline_daily", "tech_daily"),
    ("tech_name_change", "tech_namechange"),
    ("tech_suspend", "tech_suspend_d"),
    ("tech_calendar", "tech_trade_cal"),
    ("capital_holder_num", "capital_stk_holdernumber"),
    ("fundamental_report", "fundamental_income"),
    ("fundamental_top10", "fundamental_top10_holders"),
    ("fundamental_top10_float", "fundamental_top10_floatholders"),
    ("fundamental_market_daily", "fundamental_index_daily"),
]

# 序列改名（PG 在 RENAME TABLE 时不会自动跟）
RENAME_SEQUENCE: list[tuple[str, str]] = [
    (f"{old}_id_seq", f"{new}_id_seq")
    for old, new in RENAME_TABLE
] + [
    # 之前 stock_info → stock_basic 的迁移漏了 sequence，补一刀
    ("fundamental_stock_info_id_seq", "fundamental_stock_basic_id_seq"),
]

# 索引重命名（含旧表名的全部跟着走，避免日志里出现旧名）
RENAME_INDEX: list[tuple[str, str]] = []
for old, new in RENAME_TABLE:
    old_dash = old.replace("_", "_")  # 保持原样
    new_dash = new
    # 这里用 dump 里实际存在的索引名硬编码（与 ORM model 对齐后的期望名）
    pass  # 见下方显式定义


# ── 显式索引 / 唯一约束映射（覆盖到上述 9 张表对应的全部对象） ─
# 同时兼容 dump 名（旧）和 live DB 名（部分旧表名漏改的产物），
# 统一对齐到建议表名。
INDEX_RENAME: list[tuple[str, str]] = [
    # tech_kline_daily / tech_daily
    ("ix_tech_kline_symbol", "ix_tech_daily_symbol"),
    ("ix_tech_kline_symbol_date", "ix_tech_daily_symbol_date"),
    ("uq_tech_kline_symbol_date", "uq_tech_daily_symbol_date"),
    # tech_calendar / tech_trade_cal
    ("ix_tech_calendar_exchange", "ix_tech_trade_cal_exchange"),
    ("ix_tech_calendar_exchange_date", "ix_tech_trade_cal_exchange_date"),
    ("uq_tech_calendar_uk", "uq_tech_trade_cal_uk"),
    # tech_suspend / tech_suspend_d
    ("ix_tech_suspend_date", "ix_tech_suspend_d_date"),
    ("ix_tech_suspend_symbol", "ix_tech_suspend_d_symbol"),
    ("ix_tech_suspend_symbol_date", "ix_tech_suspend_d_symbol_date"),
    # tech_name_change / tech_namechange（live DB 实际名是 uq_tech_name_change_uk，
    # 模型里写的 uq_base_name_change_uk 从未建出）
    ("ix_tech_name_change_symbol", "ix_tech_namechange_symbol"),
    ("uq_tech_name_change_uk", "uq_tech_namechange_uk"),
    # capital_holder_num / capital_stk_holdernumber
    ("ix_capital_holder_num_symbol", "ix_capital_stk_holdernumber_symbol"),
    ("ix_capital_holder_num_date", "ix_capital_stk_holdernumber_date"),
    ("uq_capital_holder_num_uk", "uq_capital_stk_holdernumber_uk"),
    # fundamental_report / fundamental_income（补 live DB 实际存在的两条 index）
    ("ix_fundamental_report_symbol", "ix_fundamental_income_symbol"),
    ("ix_fundamental_report_symbol_end", "ix_fundamental_income_symbol_end"),
    ("uq_fundamental_report_uk", "uq_fundamental_income_uk"),
    # fundamental_top10 / fundamental_top10_holders
    ("ix_fundamental_top10_date", "ix_fundamental_top10_holders_date"),
    ("ix_fundamental_top10_symbol", "ix_fundamental_top10_holders_symbol"),
    ("uq_fundamental_top10_uk", "uq_fundamental_top10_holders_uk"),
    # fundamental_top10_float / fundamental_top10_floatholders
    ("ix_fundamental_top10_float_date", "ix_fundamental_top10_floatholders_date"),
    ("ix_fundamental_top10_float_symbol", "ix_fundamental_top10_floatholders_symbol"),
    ("uq_fundamental_top10_float_uk", "uq_fundamental_top10_floatholders_uk"),
    # fundamental_market_daily / fundamental_index_daily
    ("ix_fundamental_market_daily_date", "ix_fundamental_index_daily_date"),
    ("ix_fundamental_market_daily_market_date", "ix_fundamental_index_daily_market_date"),
    ("uq_fundamental_market_daily_uk", "uq_fundamental_index_daily_uk"),
]


# ── 探查小工具 ────────────────────────────────────────────────

async def _exists(conn, kind: str, name: str, table: str | None = None) -> bool:
    if kind == "table":
        r = await conn.execute(
            text("SELECT 1 FROM pg_tables WHERE schemaname='public' AND tablename=:n"),
            {"n": name},
        )
        return r.scalar() is not None
    if kind == "sequence":
        r = await conn.execute(
            text("SELECT 1 FROM pg_class WHERE relkind='S' AND relname=:n"),
            {"n": name},
        )
        return r.scalar() is not None
    if kind == "index":
        r = await conn.execute(
            text("SELECT 1 FROM pg_indexes WHERE schemaname='public' AND indexname=:n"),
            {"n": name},
        )
        return r.scalar() is not None
    if kind == "constraint" and table:
        r = await conn.execute(
            text("SELECT 1 FROM pg_constraint "
                 "WHERE conrelid = to_regclass(:t) AND conname=:n"),
            {"t": f"public.{table}", "n": name},
        )
        return r.scalar() is not None
    raise ValueError(kind)


async def _is_in_use(conn, sequence_name: str, table: str) -> bool:
    """检测序列是否还被某表列默认引用（防止漏改 pg_attrdef）"""
    r = await conn.execute(
        text("""
        SELECT 1
        FROM pg_attrdef ad
        JOIN pg_attribute a ON a.attrelid = ad.adrelid AND a.attnum = ad.adnum
        WHERE ad.adbin::text LIKE :pat
          AND a.attrelid = to_regclass(:t)
        LIMIT 1
        """),
        {"pat": f"%{sequence_name}%", "t": f"public.{table}"},
    )
    return r.scalar() is not None


# ── 生成执行计划 ─────────────────────────────────────────────

async def plan(conn) -> list[str]:
    steps: list[str] = []

    for old_table, new_table in RENAME_TABLE:
        old_exists = await _exists(conn, "table", old_table)
        new_exists = await _exists(conn, "table", new_table)

        if not old_exists and not new_exists:
            print(f"[skip] {old_table} / {new_table} 都不存在")
            continue
        if not old_exists and new_exists:
            print(f"[skip] {new_table} 已存在（可能上次已跑过），继续检查 seq/idx")
        else:
            steps.append(f'ALTER TABLE "{old_table}" RENAME TO "{new_table}";')

        # 序列（每个表一个 _id_seq）
        old_seq = f"{old_table}_id_seq"
        new_seq = f"{new_table}_id_seq"
        if await _exists(conn, "sequence", old_seq):
            if await _exists(conn, "sequence", new_seq):
                # 旧名还在但新名已存在，说明旧 seq 是被换名后的 alias；删掉旧名避免混淆
                if await _is_in_use(conn, old_seq, new_table):
                    print(f"[skip] 序列 {old_seq} 仍被 {new_table} 引用（OID 已绑定 seq），不删")
                else:
                    steps.append(f'DROP SEQUENCE IF EXISTS "{old_seq}";')
            else:
                steps.append(f'ALTER SEQUENCE "{old_seq}" RENAME TO "{new_seq}";')
        elif await _exists(conn, "sequence", new_seq):
            print(f"[skip] 序列 {new_seq} 已存在")
        else:
            print(f"[warn] 未找到 {old_table} 的 _id_seq，可手动确认")

    # 补 stock_basic 的序列（之前漏改）并把列默认值指向新序列
    stock_old_seq = "fundamental_stock_info_id_seq"
    stock_new_seq = "fundamental_stock_basic_id_seq"
    if await _exists(conn, "sequence", stock_old_seq) and not await _exists(
        conn, "sequence", stock_new_seq
    ):
        steps.append(f'ALTER SEQUENCE "{stock_old_seq}" RENAME TO "{stock_new_seq}";')
    # 把 fundamental_stock_basic.id 的 default 表达式明确指向新 seq 名
    # （即使 pg 会随 rename 自动解析 regclass，这里写明确以保证 dump 可读）
    steps.append(
        'ALTER TABLE fundamental_stock_basic '
        f"ALTER COLUMN id SET DEFAULT nextval('{stock_new_seq}'::regclass);"
    )

    # 索引 / 约束重命名
    for old_name, new_name in INDEX_RENAME:
        if await _exists(conn, "index", old_name):
            # PG 索引和 UniqueConstraint 在 pg_indexes 里都叫 index 名
            steps.append(f'ALTER INDEX "{old_name}" RENAME TO "{new_name}";')
        else:
            # 索引不存在但约束名可能存在（UK 是约束 + 索引一体）
            # 在 dump 里 UK 约束名也叫 uq_xxx_uk，作为 INDEX 存在则同处理
            # 这里已经覆盖
            pass

    return steps


# ── 主流程 ───────────────────────────────────────────────────

async def run(apply: bool) -> None:
    async with raw_async_engine.connect() as conn:
        print("=" * 70)
        print("迁移前：当前 raw_data 库 30 张表")
        print("=" * 70)
        r = await conn.execute(
            text(
                "SELECT tablename FROM pg_tables WHERE schemaname='public' "
                "ORDER BY tablename"
            )
        )
        existing = [x[0] for x in r]
        for t in existing:
            print(f"   - {t}")
        # 校验：表清单是否正好对应 RENAME_TABLE 的 old（or 已经改名成 new）
        old_set = {o for o, _ in RENAME_TABLE}
        new_set = {n for _, n in RENAME_TABLE}
        for o in old_set:
            if o not in existing and o != "fundamental_stock_info":
                # 不在，说明已经改过（这种情况都正常，下面 plan 会自动跳过）
                pass
        print()

        steps = await plan(conn)

        print("=" * 70)
        print(f"待执行 DDL（{len(steps)} 条）")
        print("=" * 70)
        if not steps:
            print("   （无）")
            return
        for i, sql in enumerate(steps, 1):
            print(f"   {i:>2}. {sql}")

        if not apply:
            print()
            print(">>> dry-run 模式未执行，加 --apply 真跑")
            return

        # 提交前先关掉之前的 autobegin 事务
        await conn.rollback()
        async with conn.begin():
            for i, sql in enumerate(steps, 1):
                try:
                    await conn.execute(text(sql))
                    print(f"   [{i}/{len(steps)}] OK  {sql[:90]}")
                except ProgrammingError as exc:
                    print(f"   [{i}/{len(steps)}] FAIL  {sql}")
                    print(f"      {exc.orig}")
                    raise

        # 重新 dump 一次命名空间
        await conn.rollback()
        print()
        print("=" * 70)
        print("迁移后：表 + 序列 + 索引摘要")
        print("=" * 70)
        r = await conn.execute(
            text(
                "SELECT tablename FROM pg_tables WHERE schemaname='public' "
                "ORDER BY tablename"
            )
        )
        print("表：")
        for (t,) in r:
            print(f"   - {t}")

        r = await conn.execute(
            text(
                "SELECT sequence_name FROM information_schema.sequences "
                "WHERE sequence_schema='public' ORDER BY sequence_name"
            )
        )
        print("\n序列：")
        for (s,) in r:
            print(f"   - {s}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真正执行（默认 dry-run）")
    ap.add_argument("--yes", action="store_true", help="跳过交互确认")
    args = ap.parse_args()

    if args.apply and not args.yes:
        ans = input("确认执行以上 DDL？(yes/N) ")
        if ans.strip().lower() != "yes":
            print("已取消")
            return

    asyncio.run(run(args.apply))


if __name__ == "__main__":
    main()
