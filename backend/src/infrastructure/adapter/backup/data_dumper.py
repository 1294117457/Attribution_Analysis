r"""数据导出：用 asyncpg server-side cursor 流式读，渲染成 COPY FROM stdin 格式。

实现策略：
1. asyncpg.connect() 拿原生连接
2. conn.cursor(query, scroll=True) 拿 server-side cursor
3. async for row in cursor: 逐批读（asyncpg 自动 chunk）
4. 写到文件时构造：
    -- COPY <table>
    COPY "public"."<table>" (...) FROM stdin;
    col1<TAB>col2<TAB>...<NL>
    ...
    \<NL>
    """

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import asyncpg

from infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)

_COPY_NULL = "\\N"      # PostgreSQL COPY 协议的 NULL 表示
_COPY_DELIM = "\t"      # 列分隔
_COPY_EOL = "\n"        # 行结束


def _quote_copy_value(value: Any) -> str:
    """把 Python 值转成 COPY 协议字符串"""
    if value is None:
        return _COPY_NULL
    if isinstance(value, bool):
        return ("t" if value else "f")
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, bytes):
        # 走 PG 字节十六进制格式：\\xDEADBEEF
        return "\\x" + value.hex()
    if isinstance(value, (list, dict)):
        # JSONB / JSON 序列化
        import json
        return json.dumps(value, ensure_ascii=False, default=str)
    # 字符串 / 日期时间
    s = str(value)
    # COPY 协议需要转义：反斜杠 / 换行 / 制表符 / 回车
    s = s.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r").replace(_COPY_DELIM, "\\t")
    return s


class DataDumper:
    """导出 PostgreSQL 表数据为 COPY FROM stdin 格式"""

    def __init__(self, conn_factory=None) -> None:
        self._conn_factory = conn_factory or self._default_connect

    @asynccontextmanager
    async def _default_connect(self) -> AsyncIterator[asyncpg.Connection]:
        url = get_settings().DATABASE_URL
        dsn = url.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(dsn=dsn)
        try:
            yield conn
        finally:
            await conn.close()

    async def dump_table(
        self,
        table: str,
        columns: list[str],
        out_fp,
    ) -> int:
        """导出单表数据。

        table: 表名
        columns: 列名列表（按顺序）
        out_fp: 文件写入器（只要求 write/flush）
        返回：写入行数
        """
        # 拿 schema
        col_list_sql = ", ".join(f'"{c}"' for c in columns)

        async with self._conn_factory() as conn:
            async with conn.transaction():
                cursor = await conn.cursor(
                    f'SELECT {col_list_sql} FROM "public"."{table}"',
                )
                row_count = 0
                col_count = len(columns)
                # 写 COPY 头
                await out_fp.write(f"-- COPY {table} ({','.join(columns)})\n")
                await out_fp.write(
                    f'COPY "public"."{table}" ({col_list_sql}) FROM stdin;\n'
                )

                # 分批读 + 写
                BATCH_SIZE = 1000
                while True:
                    rows = await cursor.fetch(BATCH_SIZE)
                    if not rows:
                        break
                    buf_lines = []
                    for row in rows:
                        cells = [_quote_copy_value(v) for v in row]
                        buf_lines.append(_COPY_DELIM.join(cells))
                        row_count += 1
                    await out_fp.write(_COPY_EOL.join(buf_lines) + _COPY_EOL)

                await out_fp.write("\\.\n\n")
                return row_count

    async def list_columns(self, table: str) -> list[str]:
        """拿表的列名（按 attnum 顺序），备份时用"""
        url = get_settings().DATABASE_URL
        dsn = url.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(dsn=dsn)
        try:
            rows = await conn.fetch(
                """
                SELECT a.attname
                FROM pg_attribute a
                WHERE a.attrelid = $1::regclass AND a.attnum > 0 AND NOT a.attisdropped
                ORDER BY a.attnum
                """,
                table,
            )
            return [r["attname"] for r in rows]
        finally:
            await conn.close()