"""启动期表结构检查：以 backend/init.sql 为唯一来源

- 全新库（init.sql 中的表一张都不存在）→ 整份执行 init.sql 建表（单事务）
- 已有库 → 只比对 表 / 列名 / 列类型 / NOT NULL，有差异打 warning，不自动改表

init.sql 由 DB 客户端（pg_dump --schema-only）导出，执行前会去掉：
  psql 元命令（\\restrict 等）、CREATE/ALTER/COMMENT ON SCHEMA public、
  OWNER TO（属主跟随当前连接用户）、SET transaction_timeout（PG17+ 才有）
"""

import logging
import re
from pathlib import Path

from sqlalchemy import text

from shared.infrastructure.persistence.orm_base import Base
from shared.infrastructure.persistence.connection import async_engine

logger = logging.getLogger(__name__)

INIT_SQL_PATH = Path(__file__).resolve().parents[3] / "init.sql"

_SKIP_LINE = re.compile(
    r"^\s*(\\|CREATE SCHEMA public\b|ALTER SCHEMA public\b|COMMENT ON SCHEMA public\b"
    r"|SET transaction_timeout\b|ALTER .+ OWNER TO .+;\s*$)"
)
_CREATE_TABLE = re.compile(r"^CREATE TABLE public\.(\w+) \((.*?)\n\);", re.S | re.M)
_COLUMN = re.compile(
    r'^"?(\w+)"?\s+(.+?)(?=\s+(?:DEFAULT|NOT NULL|NULL|COLLATE|GENERATED|CONSTRAINT)\b|$)'
)

_DB_COLUMNS_SQL = """
SELECT c.relname, a.attname, format_type(a.atttypid, a.atttypmod), a.attnotnull
FROM pg_attribute a
JOIN pg_class c ON c.oid = a.attrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
  AND a.attnum > 0 AND NOT a.attisdropped
"""

# {table: {column: (type, not_null)}}
Schema = dict[str, dict[str, tuple[str, bool]]]


def _clean_sql(raw: str) -> str:
    return "\n".join(line for line in raw.splitlines() if not _SKIP_LINE.match(line))


def _parse_tables(sql: str) -> Schema:
    tables: Schema = {}
    for name, body in _CREATE_TABLE.findall(sql):
        cols: dict[str, tuple[str, bool]] = {}
        for line in body.splitlines():
            line = line.strip().rstrip(",")
            if not line or line.startswith("CONSTRAINT"):
                continue
            m = _COLUMN.match(line)
            if m:
                cols[m.group(1)] = (m.group(2).replace("public.", ""), "NOT NULL" in line)
        tables[name] = cols
    return tables


async def _load_db_schema(conn) -> Schema:
    db: Schema = {}
    for table, col, typ, not_null in await conn.execute(text(_DB_COLUMNS_SQL)):
        db.setdefault(table, {})[col] = (typ.replace("public.", ""), not_null)
    return db


def _diff(expected: Schema, actual: Schema) -> list[str]:
    problems: list[str] = []
    for table in sorted(expected.keys() - actual.keys()):
        problems.append(f"缺少表 {table}")
    for table in sorted(actual.keys() - expected.keys()):
        problems.append(f"多余表 {table}（init.sql 中没有）")
    for table in sorted(expected.keys() & actual.keys()):
        exp, act = expected[table], actual[table]
        for col in sorted(exp.keys() - act.keys()):
            problems.append(f"{table}: 缺少列 {col}")
        for col in sorted(act.keys() - exp.keys()):
            problems.append(f"{table}: 多余列 {col}")
        for col in sorted(exp.keys() & act.keys()):
            if exp[col][0] != act[col][0]:
                problems.append(f"{table}.{col}: 类型 {act[col][0]}，init.sql 为 {exp[col][0]}")
            if exp[col][1] != act[col][1]:
                want = "NOT NULL" if exp[col][1] else "NULL"
                problems.append(f"{table}.{col}: 可空性与 init.sql（{want}）不一致")
    for table in sorted(Base.metadata.tables.keys() - expected.keys()):
        problems.append(f"ORM 模型 {table} 未写入 init.sql")
    return problems


async def ensure_schema() -> None:
    """按 init.sql 建表（全新库）或校验表结构（已有库）"""
    if not INIT_SQL_PATH.is_file():
        logger.error("未找到 %s，跳过表结构检查", INIT_SQL_PATH)
        return

    sql = _clean_sql(INIT_SQL_PATH.read_text(encoding="utf-8"))
    expected = _parse_tables(sql)

    async with async_engine.connect() as conn:
        actual = await _load_db_schema(conn)

        if not expected.keys() & actual.keys():
            logger.warning("数据库为空，按 init.sql 建表（%d 张）", len(expected))
            raw = await conn.get_raw_connection()
            driver = raw.driver_connection
            async with driver.transaction():
                await driver.execute(sql)
            logger.info("init.sql 执行完成")
            return

    problems = _diff(expected, actual)
    if problems:
        logger.warning(
            "表结构与 init.sql 不一致（%d 处），请用 DB 客户端修正后重新导出 init.sql：\n  %s",
            len(problems), "\n  ".join(problems),
        )
    else:
        logger.info("表结构与 init.sql 一致（%d 张表）", len(expected))
