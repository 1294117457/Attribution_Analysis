"""迁移后校验：ORM StockBasicDB 的表结构 vs 真实 DB

逐项比对：列名 / 类型 / 可空 / 索引 / 唯一约束
任何不一致都会打印出来，全绿则输出 "OK"。
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import text
from sqlalchemy.engine.reflection import Inspector

from contexts.market.infrastructure.persistence.models.stock_basic import StockBasicDB
from shared.infrastructure.connection.db_factory import raw_async_engine


async def main() -> None:
    table = StockBasicDB.__tablename__

    orm_cols = {c.name: c for c in StockBasicDB.__table__.columns}
    orm_indexes = {i.name for i in StockBasicDB.__table__.indexes}
    # unique=True 生成的是 UniqueConstraint，DDL 名由 PG 决定 <table>_<col>_key
    orm_uniques = {
        f"{table}_{c.name}_key" for c in StockBasicDB.__table__.columns if c.unique
    }

    async with raw_async_engine.connect() as conn:
        await conn.rollback()

        def run(sync_conn):
            insp = Inspector(sync_conn)
            db_cols = {c["name"]: c for c in insp.get_columns(table)}
            db_indexes = {i["name"] for i in insp.get_indexes(table)}
            db_uniques = set()
            for uc in insp.get_unique_constraints(table):
                db_uniques.add(uc["name"])
            for ix in insp.get_indexes(table):
                if ix.get("unique"):
                    db_uniques.add(ix["name"])

            issues: list[str] = []

            print(f"表: {table}")
            print(f"行数: {sync_conn.execute(text(f'SELECT COUNT(*) FROM {table}')).scalar()}")
            print()

            print("─" * 60)
            print("列比对")
            print("─" * 60)
            only_orm = sorted(set(orm_cols) - set(db_cols))
            only_db = sorted(set(db_cols) - set(orm_cols))
            if only_orm:
                issues.append(f"ORM 有但 DB 无: {only_orm}")
            if only_db:
                issues.append(f"DB 有但 ORM 无: {only_db}")

            for name in sorted(set(orm_cols) & set(db_cols)):
                o, d = orm_cols[name], db_cols[name]
                mark = ""
                if o.nullable != d["nullable"]:
                    mark = f"  <-- nullable 不符 ORM={o.nullable} DB={d['nullable']}"
                    issues.append(f"{name}: nullable 不符")
                print(f"  {name:<16} {str(d['type']):<22}{mark}")

            print()
            print("─" * 60)
            print("索引比对")
            print("─" * 60)
            for want in sorted(orm_indexes):
                ok = want in db_indexes
                print(f"  [{'OK' if ok else '缺失'}] {want}")
                if not ok:
                    issues.append(f"索引缺失: {want}")

            print()
            print("─" * 60)
            print("唯一约束")
            print("─" * 60)
            for want in sorted(orm_uniques):
                ok = want in db_uniques
                print(f"  [{'OK' if ok else '缺失'}] {want}")
                if not ok:
                    issues.append(f"唯一约束缺失: {want}")
            print(f"  (DB 实际: {sorted(db_uniques)})")

            print()
            print("─" * 60)
            if issues:
                print(f"发现 {len(issues)} 个不一致：")
                for i in issues:
                    print(f"  ! {i}")
            else:
                print("OK —— ORM 与 DB 完全一致")

        await conn.run_sync(run)


asyncio.run(main())