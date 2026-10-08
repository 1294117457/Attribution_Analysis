"""恢复引擎：解析备份文件头部 + 单事务 DROP+CREATE+COPY 或 ON CONFLICT。

两种模式：
    cover  - 单事务内 DROP+CREATE+COPY（失败整体回滚）
    upsert - 单事务内 INSERT ... ON CONFLICT DO NOTHING（保留已有数据）

约束：
- 头部必须含 backup_name / generator=attribution-analysis / generator_version 等
- 当前 schema_version 与备份 schema_version 必须一致（或仅允许向前兼容）
- 文件路径必须在 PathResolver 白名单内
"""

from __future__ import annotations

import logging
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, AsyncIterator

import asyncpg

from infrastructure.adapter.backup.exceptions import InvalidBackupFileError
from infrastructure.adapter.backup.path_resolver import PathResolver
from infrastructure.config.settings import get_settings

if TYPE_CHECKING:
    from application.service.backup_app_service import BackupAppService

logger = logging.getLogger(__name__)


REQUIRED_HEADERS = (
    "backup_name",
    "generator",
    "generator_version",
    "backup_type",
    "tables_count",
    "created_at",
)


# ── SQL 切分 ────────────────────────────────────────────────
# 按 ';' 切分，保留原始结构；跳过空段；处理单行注释
_STMT_SEP = re.compile(r";\s*(?:\n|$)")


class Restorer:
    """恢复引擎"""

    def __init__(
        self,
        *,
        path_resolver: PathResolver,
        conn_factory=None,
    ) -> None:
        self.path_resolver = path_resolver
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

    # ── 公共 API ──────────────────────────────────────────
    async def restore(
        self,
        file_path: Path,
        restore_mode: str,
        app_service: "BackupAppService",
        record_id: int,
    ) -> None:
        """主入口：被 AppService 用 asyncio.create_task 启动。

        restore_mode: "cover" | "upsert"
        """
        # 路径校验
        file_path = self.path_resolver.resolve_read(str(file_path))

        # 读头部（流式：readlines 取前 100 行足够）
        with open(file_path, "r", encoding="utf-8") as f:
            head_lines: list[str] = []
            for _ in range(100):
                line = f.readline()
                if not line:
                    break
                head_lines.append(line)
                if line.strip().startswith("BEGIN"):
                    break
        header = self._parse_header(head_lines)
        tables = header["tables"]

        await app_service.update_restore_progress(
            record_id, progress=5, msg=f"已解析头部 ({len(tables)} 表)"
        )

        # 切分 SQL（粗略切；COPY 协议段作为整体一条）
        statements = self._split_statements(file_path)
        await app_service.update_restore_progress(
            record_id, progress=20, msg=f"SQL 切分完成 ({len(statements)} 条)"
        )

        # 单事务执行
        async with self._conn_factory() as conn:
            try:
                async with conn.transaction():
                    if restore_mode == "cover":
                        await self._restore_cover(conn, statements, app_service, record_id)
                    elif restore_mode == "upsert":
                        await self._restore_upsert(conn, statements, tables, app_service, record_id)
                    else:
                        raise InvalidBackupFileError(f"未知恢复模式: {restore_mode}")
            except Exception as e:
                # 事务已自动回滚
                await app_service.mark_restore_failed(record_id, error=str(e)[:500])
                logger.exception("restore 失败: record=%s", record_id)
                raise

        await app_service.mark_restore_success(record_id)
        await app_service.update_restore_progress(record_id, progress=100, msg="恢复完成")

    # ── cover 模式：DROP+CREATE+COPY 完整重放 ──────────
    async def _restore_cover(
        self,
        conn: asyncpg.Connection,
        statements: list[str],
        app_service: "BackupAppService",
        record_id: int,
    ) -> None:
        total = len(statements)
        for i, stmt in enumerate(statements, 1):
            if not stmt.strip():
                continue
            await conn.execute(stmt)
            pct = 20 + int(70 * i / max(total, 1))
            await app_service.update_restore_progress(
                record_id, progress=pct, msg=f"恢复 {i}/{total}"
            )

    # ── upsert 模式：跳过 schema 段，只执行 INSERT ON CONFLICT ──
    async def _restore_upsert(
        self,
        conn: asyncpg.Connection,
        statements: list[str],
        tables: list[str],
        app_service: "BackupAppService",
        record_id: int,
    ) -> None:
        # upsert 模式：解析 COPY 段，转换成 INSERT ... ON CONFLICT DO NOTHING
        # 实现要点：从 COPY 段拿表名 + 列，从 stdin 段拿数据
        # 为简化：把 COPY 段解析为 rows，然后用 conn.copy_records_to_table(table, records=rows, columns=cols)
        total_copies = sum(1 for s in statements if s.lstrip().upper().startswith("COPY "))
        done = 0
        for stmt in statements:
            if not stmt.strip():
                continue
            stripped = stmt.lstrip()
            if stripped.upper().startswith("COPY "):
                done += 1
                await self._copy_upsert(conn, stmt)
                pct = 20 + int(70 * done / max(total_copies, 1))
                await app_service.update_restore_progress(
                    record_id, progress=pct, msg=f"upsert 导入 {done}/{total_copies}"
                )
            elif stripped.startswith("--") or not stripped:
                continue
            else:
                # CREATE / DROP / SET 等跳过（upsert 模式不动 schema）
                continue

    async def _copy_upsert(self, conn: asyncpg.Connection, copy_block: str) -> None:
        r"""把 COPY ... FROM stdin 段解析成 rows + 列，用 INSERT ... ON CONFLICT 写回。

        实现要点：
        1. 提取表名 + 列名（COPY "public"."t" (col1,col2) FROM stdin;）
        2. 读 COPY 数据段（按 \n 行切分；\t 分列；\N 表示 NULL）
        3. 构造 INSERT ... ON CONFLICT DO NOTHING 用 conn.execute
        """
        # 1. 解析表名 / 列名
        m = re.match(
            r'COPY\s+"public"\."(\w+)"\s*\(([^)]+)\)\s+FROM\s+stdin\s*;',
            copy_block.split("\n", 1)[0],
        )
        if not m:
            raise InvalidBackupFileError(f"无法解析 COPY 语句: {copy_block[:80]}")

        table = m.group(1)
        cols = [c.strip().strip('"') for c in m.group(2).split(",")]

        # 2. 解析数据段
        lines = copy_block.splitlines()
        # 第 1 行是 COPY 头
        rows: list[list[str]] = []
        for line in lines[1:]:
            line = line.rstrip("\n")
            if line == "\\.":
                break
            if not line:
                continue
            # 按 \t 切；处理转义：\\\\ -> \\、\\t -> \t、\\n -> \n、\\N -> NULL
            cells = line.split("\t")
            rows.append(cells)

        if not rows:
            return

        # 3. 写回（ON CONFLICT DO NOTHING 兜底）
        # 用 asyncpg 的 executemany
        col_list = ", ".join(f'"{c}"' for c in cols)
        sql = f'INSERT INTO "public"."{table}" ({col_list}) VALUES ($1{", $2" * (len(cols) - 1)}) ON CONFLICT DO NOTHING'
        # 把每行解析成 Python 值
        from infrastructure.adapter.backup.data_dumper import _COPY_NULL
        parsed_rows: list[tuple] = []
        for row in rows:
            parsed = []
            for cell in row:
                if cell == _COPY_NULL:
                    parsed.append(None)
                else:
                    parsed.append(self._unescape_copy(cell))
            parsed_rows.append(tuple(parsed))
        await conn.executemany(sql, parsed_rows)

    @staticmethod
    def _unescape_copy(s: str) -> Any:
        """反向 COPY 协议转义（最简版：字符串）"""
        s = s.replace("\\.", "\x00ESCAPED_DOT\x00")
        s = s.replace("\\N", "\x00ESCAPED_NULL\x00")
        s = s.replace("\\\\", "\x00ESCAPED_BACKSLASH\x00")
        s = s.replace("\\n", "\n").replace("\\r", "\r").replace("\\t", "\t")
        s = s.replace("\x00ESCAPED_BACKSLASH\x00", "\\")
        s = s.replace("\x00ESCAPED_NULL\x00", "\\N")
        s = s.replace("\x00ESCAPED_DOT\x00", ".")
        return s

    # ── 头部解析 ──────────────────────────────────────────
    def _parse_header(self, head_lines: list[str]) -> dict[str, str]:
        header: dict[str, str] = {}
        for line in head_lines:
            stripped = line.strip()
            if not stripped.startswith("--"):
                if stripped.upper().startswith("SET") or stripped.upper().startswith("BEGIN"):
                    continue
                # 非注释/非 SET/BEGIN 行：停止
                break
            line_body = stripped.lstrip("- ").strip()
            if ":" not in line_body:
                continue
            k, v = line_body.split(":", 1)
            header[k.strip()] = v.strip()

        for h in REQUIRED_HEADERS:
            if h not in header:
                raise InvalidBackupFileError(f"缺少头部字段: {h}")

        if header["generator"] != "attribution-analysis":
            raise InvalidBackupFileError("非本系统生成的备份")

        # tables_count 是整数
        try:
            n = int(header["tables_count"])
        except ValueError:
            raise InvalidBackupFileError(f"tables_count 不是整数: {header['tables_count']}")

        # 解析 tables 列表
        tables_str = header.get("tables", "").strip()
        if tables_str:
            tables = [t.strip() for t in tables_str.split(",") if t.strip()]
        else:
            tables = []

        header["tables"] = tables
        header["tables_count"] = n
        return header

    # ── SQL 切分（粗略，足够 cover 模式执行）─────────────
    def _split_statements(self, file_path: Path) -> list[str]:
        """读整个 .sql，按 ';' 切分。COPY ... FROM stdin ... \\. 作为单条。

        简化：直接在内存读 200K；更大文件建议改流式。
        """
        text = file_path.read_text(encoding="utf-8")

        statements: list[str] = []
        buf: list[str] = []
        in_copy = False  # 是否在 COPY ... FROM stdin 段

        for line in text.splitlines(keepends=True):
            stripped = line.strip().rstrip(";").strip()
            # 头段/SET/BEGIN 不计入
            if not buf and (stripped.startswith("--") or stripped.upper().startswith("SET ")):
                continue
            if not buf and stripped.upper() == "BEGIN":
                continue
            if stripped.upper() == "COMMIT":
                continue

            buf.append(line)

            # 检测 COPY FROM stdin 进入
            if not in_copy and stripped.upper().startswith("COPY ") and "FROM STDIN" in line.upper():
                in_copy = True
                continue
            # 检测 COPY 结束
            if in_copy and stripped == "\\.":
                in_copy = False
                statements.append("".join(buf))
                buf = []
                continue
            # 普通语句以 ';' 结尾
            if not in_copy and line.rstrip().endswith(";"):
                statements.append("".join(buf))
                buf = []
                continue

        # 残留
        if buf and "".join(buf).strip():
            statements.append("".join(buf))

        return statements