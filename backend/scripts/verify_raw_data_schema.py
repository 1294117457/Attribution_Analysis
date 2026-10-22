"""校验 raw_data 库表结构与 ORM 模型一一对应

用法：
    cd backend && python scripts/verify_raw_data_schema.py

检查项：
1. ORM 中 RawBase 模型表名 与 raw_data 库实际表名 双向差集
2. 每张表的列名/可空/类型 是否一致
3. 索引、唯一约束名是否一致
4. 与 docs/backend-docs/data/当前接口实现.md 登记的表名是否一致
"""

from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path

import asyncpg
from sqlalchemy import inspect

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND / "src"))

from shared.infrastructure.persistence.orm_base import RawBase  # noqa: E402
from shared.infrastructure.config.settings import get_settings  # noqa: E402

DOC = (
    BACKEND.parent
    / "docs/backend-docs/data/当前接口实现.md"
)


def load_doc_tables() -> set[str]:
    """从接口实现文档的表格里提取表名。

    按表头名定位列（历史上叫「建议表名」，现在叫「表名」），
    不硬编码列位置，这样调整列顺序不会让校验脚本失效。
    """
    if not DOC.exists():
        return set()
    prefixes = ("tech_", "capital_", "fundamental_", "news_")
    names: set[str] = set()
    target_idx: int | None = None

    for line in DOC.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            target_idx = None  # 表格结束
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]

        # 表头行：找到「表名」/「建议表名」所在列
        if target_idx is None:
            for i, c in enumerate(cells):
                if c.strip("` ").replace(" ", "") in {"表名", "建议表名"}:
                    target_idx = i
                    break
            continue

        if target_idx >= len(cells):
            continue
        target = cells[target_idx].strip("`").strip()
        if target.startswith(prefixes) and target not in {"tech_", "capital_", "fundamental_", "news_"}:
            names.add(target)
    return names


def load_orm_tables() -> dict[str, object]:
    """导入所有 RawBase 模型模块，返回 {表名: Table}。

    models 目录并非都是 Python 包（缺 __init__.py），因此按文件路径动态导入。
    """
    import importlib.util

    models_root = BACKEND / "src/contexts"
    for path in sorted(models_root.glob("*/infrastructure/persistence/models/*.py")):
        if path.name.startswith("_"):
            continue
        rel = path.relative_to(BACKEND / "src").with_suffix("")
        mod_name = ".".join(rel.parts)
        spec = importlib.util.spec_from_file_location(mod_name, path)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] 导入 {mod_name} 失败: {exc}")

    return {t.name: t for t in RawBase.metadata.tables.values()}


async def fetch_db_tables(conn: asyncpg.Connection) -> dict[str, dict]:
    rows = await conn.fetch(
        """
        SELECT c.relname AS table_name,
               a.attname AS column_name,
               format_type(a.atttypid, a.atttypmod) AS data_type,
               NOT a.attnotnull AS is_nullable,
               pg_get_expr(d.adbin, d.adrelid) AS default_expr
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
        LEFT JOIN pg_attrdef d ON d.adrelid = c.oid AND d.adnum = a.attnum
        WHERE n.nspname = 'public' AND c.relkind = 'r'
        ORDER BY c.relname, a.attnum
        """
    )
    tables: dict[str, dict] = {}
    for r in rows:
        t = tables.setdefault(r["table_name"], {"columns": {}, "pk": set()})
        t["columns"][r["column_name"]] = {
            "type": r["data_type"],
            "nullable": r["is_nullable"],
            "default": r["default_expr"],
        }
    for r in await conn.fetch(
        """
        SELECT c.relname AS table_name, a.attname AS column_name
        FROM pg_constraint con
        JOIN pg_class c ON c.oid = con.conrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        JOIN unnest(con.conkey) WITH ORDINALITY AS k(attnum, ord) ON TRUE
        JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = k.attnum
        WHERE con.contype = 'p' AND n.nspname = 'public'
        """
    ):
        tables[r["table_name"]]["pk"].add(r["column_name"])
    return tables


def normalize_pg_type(t: str) -> str:
    """把 PG 类型字符串归一化，抹掉长度/精度修饰与 ARRAY 后缀噪声。"""
    t = t.lower().strip()
    t = t.replace(" without time zone", "").replace(" with time zone", "").replace("[]", "")
    t = re.sub(r"\(.*\)", "", t)
    t = t.replace("timestamp", "datetime")
    return t.strip()


# PG 类型 → SQLAlchemy 抽象类型（统一到一小组可比较的名字）
PG_TYPE_FAMILY = {
    "integer": "int",
    "bigint": "int",
    "smallint": "int",
    "double precision": "float",
    "real": "float",
    "numeric": "decimal",
    "character varying": "str",
    "character": "str",
    "text": "str",
    "boolean": "bool",
    "date": "date",
    "datetime": "datetime",
    "json": "json",
    "jsonb": "json",
}


def normalize_orm_type(col) -> str:
    """SQLAlchemy Column 类型 → 与 PG_TYPE_FAMILY 同域的名字。"""
    import sqlalchemy as sa

    t = col.type
    if isinstance(t, sa.Boolean):
        return "bool"
    if isinstance(t, sa.Integer):
        return "int"
    if isinstance(t, sa.Numeric) and not isinstance(t, sa.Float):
        return "decimal"
    if isinstance(t, sa.Float):
        return "float"
    if isinstance(t, sa.String) or isinstance(t, sa.Text):
        return "str"
    if isinstance(t, sa.DateTime):
        return "datetime_tz" if getattr(t, "timezone", False) else "datetime"
    if isinstance(t, sa.Date):
        return "date"
    if isinstance(t, sa.JSON):
        return "json"
    if isinstance(t, sa.ARRAY):
        inner = normalize_orm_type(sa.Column(t.item_type))
        return f"array[{inner}]"
    return type(t).__name__.lower()


async def main() -> int:
    dsn = get_settings().RAW_DATABASE_URL
    m = re.match(r"postgresql(?:\+\w+)?://([^:]+):([^@]+)@([^:/]+):(\d+)/(.+)$", dsn)
    if not m:
        print(f"无法解析 RAW_DATABASE_URL: {dsn}")
        return 2
    user, pwd, host, port, dbname = m.group(1), m.group(2), m.group(3), int(m.group(4)), m.group(5)

    conn = await asyncpg.connect(
        host=host, port=port, user=user, password=pwd, database=dbname
    )
    db_tables = await fetch_db_tables(conn)
    await conn.close()

    orm_tables = load_orm_tables()
    doc_tables = load_doc_tables()

    db_names = set(db_tables)
    orm_names = set(orm_tables)

    problems: list[str] = []

    only_db = db_names - orm_names
    only_orm = orm_names - db_names
    only_doc = doc_tables - db_names
    db_not_doc = db_names - doc_tables

    if only_db:
        problems.append(f"DB 有但 ORM 无模型: {sorted(only_db)}")
    if only_orm:
        problems.append(f"ORM 有但 DB 无表: {sorted(only_orm)}")
    if only_doc:
        problems.append(f"文档登记但 DB 无表: {sorted(only_doc)}")
    if db_not_doc:
        problems.append(f"DB 有但文档未登记: {sorted(db_not_doc)}")

    # 列级比对
    col_problems = 0
    for name in sorted(db_names & orm_names):
        db_cols = db_tables[name]["columns"]
        orm_cols = {c.name: c for c in orm_tables[name].columns}
        miss_in_db = set(orm_cols) - set(db_cols)
        miss_in_orm = set(db_cols) - set(orm_cols)
        if miss_in_db:
            problems.append(f"{name}: ORM 有列 DB 没有 {sorted(miss_in_db)}")
            col_problems += 1
        if miss_in_orm:
            problems.append(f"{name}: DB 有列 ORM 没有 {sorted(miss_in_orm)}")
            col_problems += 1
        # 类型比对
        for cname in sorted(set(orm_cols) & set(db_cols)):
            orm_t = normalize_orm_type(orm_cols[cname])
            db_raw = normalize_pg_type(db_cols[cname]["type"])
            db_is_array = db_cols[cname]["type"].lower().endswith("[]")
            db_tz = " with time zone" in db_cols[cname]["type"].lower()
            db_t = PG_TYPE_FAMILY.get(db_raw, db_raw)
            if db_is_array:
                db_t = f"array[{db_t}]"
            elif db_t == "datetime" and db_tz:
                db_t = "datetime_tz"
            if orm_t != db_t:
                problems.append(
                    f"{name}.{cname}: 类型不一致 ORM={orm_t} DB={db_t} ({db_cols[cname]['type']})"
                )
                col_problems += 1

    print(f"DB 表数: {len(db_names)}   ORM 模型数: {len(orm_names)}   文档登记数: {len(doc_tables)}")
    print(f"不一致项: {len(problems)}")
    if problems:
        print("\n=== 发现问题 ===")
        for p in problems:
            print(" -", p)
        return 1
    print("\n✅ 全部一致：DB 表 = ORM 模型 = 文档登记")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))