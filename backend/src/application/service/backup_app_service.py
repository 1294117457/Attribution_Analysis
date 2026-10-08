"""Backup 应用服务（业务模块：backup/）

唯一入口：
- create_backup / restore                          后台异步任务
- get_backup / list_backups / delete_backup / etc.  同步管理类

依赖通过 port 注入（DDD.md §4）：
- session_factory:    async session 工厂（每次调 DB 方法开短 session）
- schema_version:     schema 版本校验用
- backup_engine:      备份引擎（编排 schema + data + 写文件）
- restorer:           恢复引擎
- path_resolver:      路径白名单
- max_file_size:      单文件大小限制

特殊点：
- 备份/恢复任务用 asyncio.create_task 启动；本服务内管理 _running_tasks 字典
- 进度由 BackupEngine 通过本服务的 update_progress / mark_success / mark_failed 回调写入 DB
- 进度由 Restorer 通过本服务的 update_restore_progress / mark_restore_success / mark_restore_failed 回调写入 DB
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Protocol

from sqlalchemy import text

from infrastructure.adapter.backup.engine import (
    BACKUP_EXCLUDE_TABLES,
    BackupEngine,
    FileNamer,
)
from infrastructure.adapter.backup.exceptions import (
    BackupError,
    BackupTaskRunningError,
    InvalidBackupFileError,
    PathSecurityError,
)
from infrastructure.adapter.backup.path_resolver import PathResolver
from infrastructure.adapter.backup.restorer import Restorer
from infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)


# ── Port 接口 ────────────────────────────────────────────────
class SessionFactoryPort(Protocol):
    """AsyncSession 工厂（每次调用方新建一个 session）"""
    def __call__(self): ...  # async context manager


class BackupEnginePort(Protocol):
    """备份引擎抽象接口"""
    async def run(self, record_id: int, req: Any) -> None: ...


class RestorerPort(Protocol):
    """恢复引擎抽象接口"""
    async def restore(
        self,
        file_path: Path,
        restore_mode: str,
        app_service: "BackupAppService",
        record_id: int,
    ) -> None: ...


# ── 状态常量 ────────────────────────────────────────────────
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"
STATUS_INTERRUPTED = "interrupted"  # 服务重启时

# ── 恢复模式常量 ────────────────────────────────────────────
RESTORE_COVER = "cover"
RESTORE_UPSERT = "upsert"

# ── 备份粒度常量 ────────────────────────────────────────────
BACKUP_FULL = "full"
BACKUP_SCHEMA = "schema"
BACKUP_DATA = "data"

# ── 来源类型常量 ────────────────────────────────────────────
SOURCE_HISTORY = "history"
SOURCE_UPLOAD = "upload"
SOURCE_FILE = "file"


class BackupAppService:
    """Backup 业务编排 + 异步任务管理"""

    def __init__(
        self,
        *,
        session_factory: SessionFactoryPort,
        path_resolver: PathResolver,
        backup_engine: Optional["BackupEngine"] = None,
        restorer: "Restorer",
    ) -> None:
        self._session_factory = session_factory
        self.path_resolver = path_resolver
        self._backup_engine = backup_engine  # 允许 None，DI 时构造后再注入
        self._restorer = restorer
        self._file_namer = FileNamer()

        # 内存任务表：{ record_id: asyncio.Task }
        self._running_tasks: dict[int, asyncio.Task] = {}

        # 配置快照（避免每次调 get_settings）
        self._settings = get_settings()

    def attach_backup_engine(self, engine: "BackupEngine") -> None:
        """DI 工厂在构造 BackupEngine 之后调用此方法注入 engine。

        解决循环依赖：BackupEngine 需要 app_service 做进度回调，
        但 AppService 又持有 BackupEngine。
        """
        self._backup_engine = engine

    # ═════════════════════════════════════════════════════
    #  备份
    # ═════════════════════════════════════════════════════
    async def create_backup(self, req: Any, user_id: int) -> int:
        """创建备份任务（异步执行）

        req 字段：backup_type / scope / tables / output_dir / name
        返回：record_id
        """
        await self._assert_no_running_backup()

        all_tables = self._list_all_tables()
        if req.scope == "all":
            tables = list(all_tables)
        else:
            requested = set(req.tables or [])
            tables = [t for t in all_tables if t in requested]
            if not tables:
                raise ValueError("至少选择一张表")

        tables = [t for t in tables if t not in BACKUP_EXCLUDE_TABLES]

        # 解析 output_dir
        out_dir = self.path_resolver.resolve_write(req.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        output_dir_str = str(out_dir)

        # 生成默认名
        name = req.name or self._file_namer.make(req.backup_type, len(tables))

        async with self._session_factory() as session:
            row_result = await session.execute(
                text("""
                    INSERT INTO sys_backup_records (
                        name, backup_type, scope, tables, tables_count,
                        output_dir, status, created_by
                    ) VALUES (
                        :name, :bt, :scope, CAST(:tables AS jsonb), :tc,
                        :od, 'pending', :uid
                    ) RETURNING id
                """),
                {
                    "name": name,
                    "bt": req.backup_type,
                    "scope": req.scope,
                    "tables": str(tables).replace("'", '"'),
                    "tc": len(tables),
                    "od": output_dir_str,
                    "uid": user_id,
                },
            )
            record_id = row_result.scalar_one()
            await session.commit()

        # 启动异步任务
        task = asyncio.create_task(
            self._safe_run_backup(record_id, req),
            name=f"backup-{record_id}",
        )
        self._running_tasks[record_id] = task
        return record_id

    async def _safe_run_backup(self, record_id: int, req: Any) -> None:
        try:
            await self._backup_engine.run(record_id, req)
        except Exception as e:
            logger.exception("backup task 异常: record=%s", record_id)
            await self.mark_failed(record_id, error=str(e)[:500])
        finally:
            self._running_tasks.pop(record_id, None)

    # ── 进度 / 状态 ───────────────────────────────
    async def update_progress(self, record_id: int, progress: int, msg: str) -> None:
        """被 BackupEngine 回调"""
        try:
            async with self._session_factory() as session:
                await session.execute(
                    text("""
                        UPDATE sys_backup_records
                        SET status = 'running',
                            progress = :p,
                            progress_msg = :m,
                            started_at = COALESCE(started_at, NOW())
                        WHERE id = :id
                    """),
                    {"p": progress, "m": msg[:255], "id": record_id},
                )
                await session.commit()
        except Exception as e:
            logger.warning("update_progress 失败: record=%s, err=%s", record_id, e)

    async def mark_success(self, record_id: int, *, file_path: Path = None, file_size: int = None) -> None:
        async with self._session_factory() as session:
            await session.execute(
                text("""
                    UPDATE sys_backup_records
                    SET status = 'success',
                        progress = 100,
                        progress_msg = '完成',
                        file_path = :fp,
                        file_size = :fs,
                        finished_at = NOW()
                    WHERE id = :id
                """),
                {"fp": str(file_path) if file_path else None,
                 "fs": file_size if file_size else None,
                 "id": record_id},
            )
            await session.commit()

    async def mark_failed(self, record_id: int, *, error: str = "") -> None:
        async with self._session_factory() as session:
            await session.execute(
                text("""
                    UPDATE sys_backup_records
                    SET status = 'failed',
                        error_message = :err,
                        finished_at = NOW()
                    WHERE id = :id
                """),
                {"err": error[:500], "id": record_id},
            )
            await session.commit()

    # ── 列表 / 单条 / 删除 / 下载 ────────────────
    async def list_backups(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
    ) -> tuple[list[dict], int]:
        offset = (page - 1) * page_size
        params: dict = {"limit": page_size, "offset": offset}
        where = ""
        if status:
            where = "WHERE status = :status"
            params["status"] = status

        async with self._session_factory() as session:
            rows = (await session.execute(
                text(f"""
                    SELECT id, name, backup_type, scope, tables, tables_count,
                           output_dir, file_path, file_size, row_count,
                           progress, progress_msg, status, error_message,
                           started_at, finished_at, created_by, created_at
                    FROM sys_backup_records
                    {where}
                    ORDER BY id DESC
                    LIMIT :limit OFFSET :offset
                """),
                params,
            )).mappings().all()
            total = (await session.execute(
                text(f"SELECT COUNT(*) FROM sys_backup_records {where}"),
                params,
            )).scalar_one()

            items = []
            for r in rows:
                d = dict(r)
                # JSONB → list
                if isinstance(d.get("tables"), str):
                    import json
                    d["tables"] = json.loads(d["tables"])
                items.append(d)
            return items, total

    async def get_backup(self, record_id: int) -> Optional[dict]:
        async with self._session_factory() as session:
            row = (await session.execute(
                text("""
                    SELECT id, name, backup_type, scope, tables, tables_count,
                           output_dir, file_path, file_size, row_count,
                           progress, progress_msg, status, error_message,
                           started_at, finished_at, created_by, created_at
                    FROM sys_backup_records WHERE id = :id
                """),
                {"id": record_id},
            )).mappings().first()
            if not row:
                return None
            d = dict(row)
            if isinstance(d.get("tables"), str):
                import json
                d["tables"] = json.loads(d["tables"])
            return d

    async def delete_backup(self, record_id: int) -> None:
        # 校验不是 running
        async with self._session_factory() as session:
            row = (await session.execute(
                text("SELECT status, file_path FROM sys_backup_records WHERE id = :id"),
                {"id": record_id},
            )).first()
            if not row:
                raise BackupError(f"备份不存在: {record_id}")
            status, file_path = row
            if status == STATUS_RUNNING or status == STATUS_PENDING:
                raise BackupTaskRunningError(f"备份任务在跑/排队中，不能删除")

            # 删文件
            if file_path:
                p = Path(file_path)
                if p.exists() and p.is_file():
                    try:
                        p.unlink()
                    except Exception as e:
                        logger.warning("删除 .sql 文件失败: %s, err=%s", p, e)

            # 删 row
            await session.execute(
                text("DELETE FROM sys_backup_records WHERE id = :id"),
                {"id": record_id},
            )
            await session.commit()

    async def get_download_path(self, record_id: int) -> Path:
        async with self._session_factory() as session:
            row = (await session.execute(
                text("SELECT file_path, status FROM sys_backup_records WHERE id = :id"),
                {"id": record_id},
            )).first()
            if not row:
                raise BackupError(f"备份不存在: {record_id}")
            file_path, status = row
            if status != STATUS_SUCCESS:
                raise BackupError(f"备份未成功: status={status}")
            if not file_path:
                raise BackupError("备份文件不存在")
            return Path(file_path)

    # ── 表元信息 ──────────────────────────────────
    async def list_tables(self) -> list[dict]:
        """返回 [{name, row_count, size_mb, category}, ...]"""
        async with self._session_factory() as session:
            rows = (await session.execute(
                text("""
                    SELECT
                        c.relname AS name,
                        c.reltuples::bigint AS row_count,
                        pg_total_relation_size(c.oid) / 1024 / 1024.0 AS size_mb
                    FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE n.nspname = 'public'
                      AND c.relkind = 'r'
                      AND c.relname != 'pg_stat_statements'
                    ORDER BY c.relname
                """)
            )).mappings().all()
            items = []
            for r in rows:
                name = r["name"]
                category = self._categorize(name)
                items.append({
                    "name": name,
                    "row_count": int(r["row_count"]),
                    "size_mb": round(float(r["size_mb"]), 2),
                    "category": category,
                })
            return items

    @staticmethod
    def _categorize(name: str) -> str:
        if name.startswith("sys_"):
            return "system"
        if name.endswith("_dailys") or name.startswith("tech_") or name.startswith("mkt_"):
            return "market"
        if name.startswith("cap_") or name.startswith("fin_") or name.startswith("base_"):
            return "financial"
        if name.startswith("concept_") or name.startswith("concepts"):
            return "concept"
        return "business"

    # ── 配置 ──────────────────────────────────────
    async def get_backup_config(self) -> dict:
        return {
            "default_output_dir": self._settings.BACKUP_DIR,
            "allowed_roots": self._settings.BACKUP_ALLOWED_ROOTS,
            "schema_version": self._settings.BACKUP_SCHEMA_VERSION,
            "max_file_size": self._settings.BACKUP_MAX_FILE_SIZE,
        }

    async def update_backup_config(self, req: Any, user_id: int) -> None:
        """v1 简化：只写到内存（重启后回退到 settings 默认值）

        生产环境需要持久化到 DB 时再加 sys_app_config 表
        """
        # 简单实现：写日志 + 校验
        if req.default_output_dir is not None:
            # 校验路径在白名单
            p = self.path_resolver.resolve_write(req.default_output_dir)
            logger.info("update_backup_config: default_output_dir=%s (user=%s)", p, user_id)
        if req.allowed_roots is not None:
            for r in req.allowed_roots:
                self.path_resolver.resolve_write(r)  # 校验
            logger.info("update_backup_config: allowed_roots=%s (user=%s)", req.allowed_roots, user_id)
        # v1 不持久化

    # ═════════════════════════════════════════════════════
    #  恢复
    # ═════════════════════════════════════════════════════
    async def create_restore(self, req: Any, user_id: int) -> int:
        if not getattr(req, "confirm", False):
            raise BackupError("恢复操作必须 confirm=True")

        await self._assert_no_running_restore()

        # 解析源
        source_path, source_type, source_backup_id = self._resolve_restore_source(req)

        async with self._session_factory() as session:
            row_result = await session.execute(
                text("""
                    INSERT INTO sys_restore_records (
                        name, source_type, source_path, source_backup_id,
                        restore_mode, status, created_by
                    ) VALUES (
                        :name, :st, :sp, :sbid,
                        :rm, 'pending', :uid
                    ) RETURNING id
                """),
                {
                    "name": f"restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "st": source_type,
                    "sp": str(source_path),
                    "sbid": source_backup_id,
                    "rm": req.restore_mode,
                    "uid": user_id,
                },
            )
            record_id = row_result.scalar_one()
            await session.commit()

        task = asyncio.create_task(
            self._safe_run_restore(record_id, req, source_path),
            name=f"restore-{record_id}",
        )
        self._running_tasks[record_id] = task
        return record_id

    def _resolve_restore_source(self, req: Any) -> tuple[Path, str, Optional[int]]:
        if req.source_type == SOURCE_HISTORY:
            if not req.source_backup_id:
                raise BackupError("history 模式必须提供 source_backup_id")
            # 异步读（这里同步读，需要特殊处理）
            # 简化——调用方传 file_path 进来
            raise BackupError("history 模式暂未实现，请使用 upload/file 模式")
        elif req.source_type == SOURCE_UPLOAD:
            if not req.upload_id:
                raise BackupError("upload 模式必须提供 upload_id")
            upload_path = Path(self._settings.BACKUP_DIR) / "_uploads" / req.upload_id
            return upload_path, SOURCE_UPLOAD, None
        elif req.source_type == SOURCE_FILE:
            if not req.source_path:
                raise BackupError("file 模式必须提供 source_path")
            return Path(req.source_path), SOURCE_FILE, None
        else:
            raise BackupError(f"未知 source_type: {req.source_type}")

    async def _safe_run_restore(self, record_id: int, req: Any, source_path: Path) -> None:
        try:
            await self._restore_record_start(record_id)
            await self._restorer.restore(
                file_path=source_path,
                restore_mode=req.restore_mode,
                app_service=self,
                record_id=record_id,
            )
        except Exception as e:
            logger.exception("restore task 异常: record=%s", record_id)
            await self.mark_restore_failed(record_id, error=str(e)[:500])
        finally:
            self._running_tasks.pop(record_id, None)

    async def _restore_record_start(self, record_id: int) -> None:
        async with self._session_factory() as session:
            await session.execute(
                text("""
                    UPDATE sys_restore_records
                    SET status = 'running',
                        started_at = NOW(),
                        progress = 0
                    WHERE id = :id
                """),
                {"id": record_id},
            )
            await session.commit()

    async def mark_restore_failed(self, record_id: int, *, error: str = "") -> None:
        async with self._session_factory() as session:
            await session.execute(
                text("""
                    UPDATE sys_restore_records
                    SET status = 'failed',
                        error_message = :err,
                        finished_at = NOW()
                    WHERE id = :id
                """),
                {"err": error, "id": record_id},
            )
            await session.commit()

    async def mark_restore_success(self, record_id: int) -> None:
        async with self._session_factory() as session:
            await session.execute(
                text("""
                    UPDATE sys_restore_records
                    SET status = 'success',
                        progress = 100,
                        progress_msg = '完成',
                        finished_at = NOW()
                    WHERE id = :id
                """),
                {"id": record_id},
            )
            await session.commit()

    async def list_restores(self, *, page: int = 1, page_size: int = 20) -> tuple[list[dict], int]:
        offset = (page - 1) * page_size
        async with self._session_factory() as session:
            rows = (await session.execute(
                text("""
                    SELECT id, name, source_type, source_path, source_backup_id,
                           restore_mode, tables, tables_count, pre_backup_id,
                           progress, progress_msg, status, rows_inserted, rows_skipped,
                           error_message, started_at, finished_at, created_by, created_at
                    FROM sys_restore_records
                    ORDER BY id DESC
                    LIMIT :limit OFFSET :offset
                """),
                {"limit": page_size, "offset": offset},
            )).mappings().all()
            total = (await session.execute(
                text("SELECT COUNT(*) FROM sys_restore_records"),
            )).scalar_one()
            items = []
            for r in rows:
                d = dict(r)
                if isinstance(d.get("tables"), str):
                    import json
                    d["tables"] = json.loads(d["tables"])
                items.append(d)
            return items, total

    async def get_restore(self, record_id: int) -> Optional[dict]:
        async with self._session_factory() as session:
            row = (await session.execute(
                text("""
                    SELECT id, name, source_type, source_path, source_backup_id,
                           restore_mode, tables, tables_count, pre_backup_id,
                           progress, progress_msg, status, rows_inserted, rows_skipped,
                           error_message, started_at, finished_at, created_by, created_at
                    FROM sys_restore_records WHERE id = :id
                """),
                {"id": record_id},
            )).mappings().first()
            if not row:
                return None
            d = dict(row)
            if isinstance(d.get("tables"), str):
                import json
                d["tables"] = json.loads(d["tables"])
            return d

    # ═════════════════════════════════════════════════════
    #  上传
    # ═════════════════════════════════════════════════════
    async def upload_backup_file(self, file_content: bytes, filename: str, user_id: int) -> dict:
        """落地 .sql 到 BACKUP_DIR/_uploads/，返回 upload_id + 头部信息"""
        upload_dir = self.path_resolver.resolve_upload()
        # 安全文件名
        safe_name = re.sub(r"[^A-Za-z0-9_\-\.]", "_", filename)[:80]
        # 用时间戳 + 随机后缀
        upload_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename[:16]}"
        target_path = upload_dir / upload_id

        # 写
        with open(target_path, "wb") as f:
            f.write(file_content)

        size = len(file_content)
        if size > self._settings.BACKUP_MAX_FILE_SIZE:
            target_path.unlink(missing_ok=True)
            raise BackupError(f"文件超过最大限制: {size} > {self._settings.BACKUP_MAX_FILE_SIZE}")

        # 解析头部（简单校验）
        try:
            head_text = file_content.decode("utf-8", errors="replace")
            head_lines = head_text.splitlines()[:50]
            header = {}
            for line in head_lines:
                s = line.strip()
                if not s.startswith("--"):
                    break
                body = s.lstrip("- ").strip()
                if ":" in body:
                    k, v = body.split(":", 1)
                    header[k.strip()] = v.strip()
            if header.get("generator") != "attribution-analysis":
                target_path.unlink(missing_ok=True)
                raise InvalidBackupFileError("非本系统生成的备份")
        except InvalidBackupFileError:
            raise
        except Exception as e:
            target_path.unlink(missing_ok=True)
            raise InvalidBackupFileError(f"解析头部失败: {e}")

        return {
            "upload_id": str(target_path),
            "filename": safe_name,
            "size": size,
            "header": header,
        }

    # ═════════════════════════════════════════════════════
    #  工具
    # ═════════════════════════════════════════════════════
    async def _assert_no_running_backup(self) -> None:
        async with self._session_factory() as session:
            cnt = (await session.execute(
                text("SELECT COUNT(*) FROM sys_backup_records WHERE status IN ('pending','running')"),
            )).scalar_one()
            if cnt > 0:
                raise BackupTaskRunningError("已有备份任务在跑")

    async def _assert_no_running_restore(self) -> None:
        async with self._session_factory() as session:
            cnt = (await session.execute(
                text("SELECT COUNT(*) FROM sys_restore_records WHERE status IN ('pending','running')"),
            )).scalar_one()
            if cnt > 0:
                raise BackupTaskRunningError("已有恢复任务在跑")

    def _list_all_tables(self) -> list[str]:
        """从 SQLAlchemy Base.metadata 拿所有表名"""
        from infrastructure.persistence.base import Base
        return list(Base.metadata.tables.keys())

    async def recover_interrupted_tasks(self) -> None:
        """启动时调用：把 running/pending 标记为 failed"""
        async with self._session_factory() as session:
            try:
                await session.execute(
                    text("""
                        UPDATE sys_backup_records
                        SET status = 'failed',
                            error_message = COALESCE(error_message, '') || ' [服务重启]',
                            finished_at = NOW()
                        WHERE status IN ('pending', 'running')
                    """),
                )
                await session.execute(
                    text("""
                        UPDATE sys_restore_records
                        SET status = 'failed',
                            error_message = COALESCE(error_message, '') || ' [服务重启]',
                            finished_at = NOW()
                        WHERE status IN ('pending', 'running')
                    """),
                )
                await session.commit()
            except Exception as e:
                logger.warning("recover_interrupted_tasks 跳过: %s", e)

    # 进度回调用于 restorer 调用
    async def update_restore_progress(self, record_id: int, progress: int, msg: str) -> None:
        async with self._session_factory() as session:
            await session.execute(
                text("""
                    UPDATE sys_restore_records
                    SET progress = :p, progress_msg = :m
                    WHERE id = :id
                """),
                {"p": progress, "m": msg[:255], "id": record_id},
            )
            await session.commit()