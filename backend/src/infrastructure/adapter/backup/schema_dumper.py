"""Schema 渲染：用 asyncpg 直接反射 PostgreSQL 表结构，渲染成 CREATE TABLE 语句。

不走 SQLAlchemy Inspector（异步版本麻烦），直接用 asyncpg 拿 pg_catalog。

实现策略：
1. asyncpg.connect(DATABASE_URL) 拿原生连接
2. 查 pg_catalog 拿列信息、主键 / 唯一 / 非空 / 默认值
3. 查 pg_indexes 拿索引
4. 查 pg_constraint 拿外键、CHECK 约束
5. 拼接 CREATE TABLE / CREATE INDEX 语句
"""

from __future__ import annotations

import logging
from typing import AsyncIterator

import asyncpg

from infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)


# ── 数据类型映射 ────────────────────────────────────────────
# pg_type → CREATE TABLE 类型
# 简化版：覆盖项目里实际出现的几十种类型，未覆盖的走 DEFAULT
_TYPE_MAP = {
    "smallint": "SMALLINT",
    "integer": "INTEGER",
    "bigint": "BIGINT",
    "numeric": "NUMERIC",
    "real": "REAL",
    "double precision": "DOUBLE PRECISION",
    "character varying": "VARCHAR",
    "varchar": "VARCHAR",
    "character": "CHAR",
    "char": "CHAR",
    "text": "TEXT",
    "bytea": "BYTEA",
    "boolean": "BOOLEAN",
    "date": "DATE",
    "time without time zone": "TIME",
    "time with time zone": "TIMETZ",
    "timestamp without time zone": "TIMESTAMP",
    "timestamp with time zone": "TIMESTAMPTZ",
    "jsonb": "JSONB",
    "json": "JSON",
    "uuid": "UUID",
}


def _format_default(default_expr: str | None) -> str:
    """把 pg_attrdef 的 binary 字段默认值转成 SQL 标准"""
    if not default_expr:
        return ""
    s = default_expr.strip()
    # nextval('xxx'::regclass) → 序列默认
    if s.startswith("nextval("):
        return f"DEFAULT {s}"
    # 普通字面量
    return f"DEFAULT {s}"


class SchemaDumper:
    """从 PostgreSQL 反射 CREATE TABLE / DROP TABLE / CREATE INDEX"""

    def __init__(self, conn_factory=None) -> None:
        """conn_factory: 可选外部注入 asyncpg 连接工厂（如测试用）；
        不传则自己从 DATABASE_URL 建连。"""
        self._conn_factory = conn_factory or self._default_connect

    async def _default_connect(self) -> AsyncIterator[asyncpg.Connection]:
        """默认连接工厂：从 DATABASE_URL 解析 + asyncpg.connect"""
        url = get_settings().DATABASE_URL
        # asyncpg 不直接吃 SQLAlchemy URL，需要把 postgresql+asyncpg:// 剥成 postgresql://
        dsn = url.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(dsn=dsn)
        try:
            yield conn
        finally:
            await conn.close()

    # ── 公共 API ─────────────────────────────────────────
    async def dump_tables(
        self,
        table_names: list[str],
        out_fp,
    ) -> None:
        """把所有 CREATE / DROP / INDEX 语句写到 out_fp（流式）。

        out_fp: 任意带 write/str 关闭的对象（async / sync 都行）。
                为统一，本方法只要求有 write 方法。
        """
        async with self._conn_factory() as conn:
            for table in table_names:
                await out_fp.write(f'DROP TABLE IF EXISTS "public"."{table}" CASCADE;\n')
                create_sql, indexes_sql = await self._build_create_table(conn, table)
                await out_fp.write(create_sql + "\n")
                for idx_sql in indexes_sql:
                    await out_fp.write(idx_sql + "\n")

    # ── 内部：拿单表所有信息 ─────────────────────────────
    async def _build_create_table(
        self,
        conn: asyncpg.Connection,
        table: str,
    ) -> tuple[str, list[str]]:
        """返回 (CREATE TABLE 语句, INDEX 字符串列表)"""
        # 1. 表是否存在
        exists = await conn.fetchval(
            "SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=$1",
            table,
        )
        if not exists:
            raise ValueError(f"表不存在: {table}")

        # 2. 列
        cols = await conn.fetch(
            """
            SELECT a.attnum, a.attname, t.typname AS type_oid_name,
                   format_type(a.atttypid, a.atttypmod) AS type_full,
                   a.attnotnull, pg_get_expr(d.adbin, d.adrelid) AS default_expr,
                   col_description(a.attrelid, a.attnum) AS comment
            FROM pg_attribute a
            JOIN pg_type t ON t.oid = a.atttypid
            LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
            WHERE a.attrelid = $1::regclass AND a.attnum > 0 AND NOT a.attisdropped
            ORDER BY a.attnum
            """,
            table,
        )

        # 3. 主键
        pk_cols = await conn.fetch(
            """
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = $1::regclass AND i.indisprimary
            ORDER BY array_position(i.indkey, a.attnum)
            """,
            table,
        )
        pk_list = [r["name"] for r in pk_cols]

        # 4. 构造 CREATE TABLE
        col_lines = []
        for c in cols:
            parts = [f'"{c["name"]}"', c["type_full"]]
            if c["default_expr"]:
                parts.append(_format_default(c["default_expr"]))
            if c["attnotnull"] or c["name"] in pk_list:
                parts.append("NOT NULL")
            col_lines.append("    " + " ".join(parts))
        if pk_list:
            pk_str = ", ".join(f'"{n}"' for n in pk_list)
            col_lines.append(f"    PRIMARY KEY ({pk_str})")

        create_sql = f'CREATE TABLE "public"."{table}" (\n'
        create_sql += ",\n".join(col_lines) + "\n);\n"

        # 5. 索引（PK 自动建不算；其余单拿）
        indexes = await conn.fetch(
            """
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE schemaname='public' AND tablename=$1
              AND indexname NOT LIKE '%_pkey'
            """,
            table,
        )
        index_sqls = [r["indexdef"] + ";" for r in indexes]
        return create_sql, index_sqls