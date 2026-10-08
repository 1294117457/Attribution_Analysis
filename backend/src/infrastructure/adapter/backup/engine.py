"""备份引擎：编排 schema_dumper + data_dumper，写 .sql 文件，回报进度。

设计要点：
- run() 被 application/service/backup_app_service.py 通过 asyncio.create_task 启动
- 进度通过回调 app_service.update_progress(record_id, progress, msg) 上报
- 文件名生成器 FileNamer 内嵌在本文件（v1 不独立）

文件格式：纯 SQL 文本
    -- 头部注释（备份名 / 类型 / 表 / 时间 / schema_version）
    SET 客户端 SQL;
    BEGIN;
    <schema_dumper 输出>
    <data_dumper 输出>
    COMMIT;

恢复时校验头部、generator=attribution-analysis、按表 schema → 切 COPY → 顺序执行。
"""

from __future__ import annotations

import logging
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiofiles

from infrastructure.adapter.backup.exceptions import PathSecurityError
from infrastructure.adapter.backup.path_resolver import PathResolver
from infrastructure.config.settings import get_settings

if TYPE_CHECKING:
    from application.service.backup_app_service import BackupAppService

logger = logging.getLogger(__name__)


# ── 备份排除表 ────────────────────────────────────────────
# 这些表不参与备份（自备份无意义）
BACKUP_EXCLUDE_TABLES: set[str] = {
    "sys_backup_records",
    "sys_restore_records",
}

SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_\-]")


class FileNamer:
    """文件名生成器

    full   : full_YYYYMMDD_HHMMSS_<随机8>.sql
    schema : schema_YYYYMMDD_HHMMSS_<随机8>.sql
    data   : data_YYYYMMDD_HHMMSS_<随机8>.sql
    """

    def make(self, backup_type: str, tables_count: int, user_name: str = "") -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = secrets.token_hex(4)  # 8 字符防冲突
        prefix = (
            self._sanitize(user_name) if user_name
            else f"{backup_type}_{ts}_{tables_count}t"
        )
        return f"{prefix}_{suffix}.sql"

    def make_default_name(self, backup_type: str) -> str:
        return f"{backup_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    @staticmethod
    def _sanitize(name: str) -> str:
        return SAFE_NAME_RE.sub("_", name)[:80]


class BackupEngine:
    """备份引擎：编排 + 写文件 + 进度上报

    依赖注入：
    - schema_dumper, data_dumper: 用于 dump
    - path_resolver: 路径白名单
    - app_service: 进度回调（用 update_progress / mark_success / mark_failed）
    """

    def __init__(
        self,
        *,
        schema_dumper,
        data_dumper,
        path_resolver: PathResolver,
        app_service: "BackupAppService",
    ) -> None:
        self.schema_dumper = schema_dumper
        self.data_dumper = data_dumper
        self.path_resolver = path_resolver
        self.app_service = app_service
        self.file_namer = FileNamer()

    # ── 主入口 ──────────────────────────────────────────
    async def run(self, record_id: int, req: Any) -> None:
        """被 AppService 用 asyncio.create_task 启动。

        req: 必须是具有以下字段的对象（DTO）：
          - backup_type: Literal["full", "schema", "data"]
          - scope: Literal["all", "partial"]
          - tables: list[str] | None
          - output_dir: str | None
          - name: str | None
        """
        # 解析输出目录
        out_dir = self.path_resolver.resolve_write(req.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        # 决定备份表
        all_tables = self._list_all_tables()
        if req.scope == "all":
            tables = list(all_tables)
        else:
            requested = set(req.tables or [])
            tables = [t for t in all_tables if t in requested]
            missing = requested - set(tables)
            if missing:
                raise ValueError(f"未知表: {sorted(missing)}")

        # 排除
        tables = [t for t in tables if t not in BACKUP_EXCLUDE_TABLES]
        if not tables:
            raise ValueError("没有可备份的表（可能全在 BACKUP_EXCLUDE_TABLES）")

        # 文件名
        file_name = req.name or self.file_namer.make(req.backup_type, len(tables))
        # 安全：禁止路径分隔符
        if "/" in file_name or "\\" in file_name:
            raise PathSecurityError(f"文件名不能含路径分隔符: {file_name}")
        file_path = out_dir / file_name

        # 写文件
        await self.app_service.update_progress(
            record_id, progress=5, msg=f"开始 {req.backup_type} 备份（{len(tables)} 表）"
        )

        settings = get_settings()
        try:
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                # 头部
                header = self._render_header(req, tables)
                await f.write(header)
                await self.app_service.update_progress(
                    record_id, progress=10, msg="写头部完成"
                )

                # schema 段
                if req.backup_type in ("full", "schema"):
                    await self.schema_dumper.dump_tables(tables, f)
                    await self.app_service.update_progress(
                        record_id, progress=20, msg="schema 完成"
                    )

                # data 段
                if req.backup_type in ("full", "data"):
                    total_rows = 0
                    for i, table in enumerate(tables, 1):
                        columns = await self.data_dumper.list_columns(table)
                        rows = await self.data_dumper.dump_table(table, columns, f)
                        total_rows += rows
                        pct = 20 + int(70 * i / len(tables))
                        await self.app_service.update_progress(
                            record_id,
                            progress=pct,
                            msg=f"已导出 {table} ({i}/{len(tables)}, {rows} 行)",
                        )

                await f.write("\nCOMMIT;\n")

            # 成功后回报
            file_size = file_path.stat().st_size
            await self.app_service.mark_success(
                record_id=record_id,
                file_path=file_path,
                file_size=file_size,
            )
            logger.info(
                "backup 完成: record=%s, file=%s, size=%d",
                record_id, file_path, file_size,
            )
        except Exception as e:
            # 失败：清理残留文件 + 回报
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception:
                pass
            await self.app_service.mark_failed(record_id, error=str(e)[:500])
            logger.exception("backup 失败: record=%s", record_id)
            raise

    # ── 内部 ──────────────────────────────────────────
    def _render_header(self, req: Any, tables: list[str]) -> str:
        """写头部注释 + SET 语句"""
        settings = get_settings()
        ts = datetime.now(timezone.utc).isoformat()
        backup_name = req.name or self.file_namer.make_default_name(req.backup_type)
        lines = [
            "-- backup_name: " + backup_name,
            "-- generator: attribution-analysis",
            f"-- generator_version: 1.0",
            f"-- backup_type: {req.backup_type}",
            f"-- scope: {req.scope}",
            f"-- tables_count: {len(tables)}",
            f"-- tables: {','.join(tables)}",
            f"-- created_at: {ts}",
            f"-- schema_version: {settings.BACKUP_SCHEMA_VERSION}",
            "",
            "SET client_encoding = 'UTF8';",
            "SET standard_conforming_strings = on;",
            "SET session_replication_role = 'origin';",
            "BEGIN;",
            "",
        ]
        return "\n".join(lines)

    def _list_all_tables(self) -> list[str]:
        """从 SQLAlchemy Base.metadata 拿所有表名

        必须在 main.py 模块加载后调用（main.py 第 35-69 行 import 了所有 ORM）
        """
        # 延迟导入，避循环
        from infrastructure.persistence.models import (
            TechKlineDailyDB,  # noqa: F401
            StockInfoDB,      # noqa: F401
        )
        from infrastructure.persistence.base import Base
        return list(Base.metadata.tables.keys())