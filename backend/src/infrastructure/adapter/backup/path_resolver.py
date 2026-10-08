"""路径白名单 + 安全校验

读 / 写路径必须落在 settings.BACKUP_ALLOWED_ROOTS 任一根目录下。
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from infrastructure.adapter.backup.exceptions import (
    InvalidBackupFileError,
    PathSecurityError,
)
from infrastructure.config.settings import get_settings


class PathResolver:
    """路径白名单 + 安全校验"""

    def __init__(self, allowed_roots: Iterable[str] | None = None) -> None:
        if allowed_roots is None:
            allowed_roots = get_settings().BACKUP_ALLOWED_ROOTS
        self._allowed_roots: list[Path] = [Path(r).resolve() for r in allowed_roots]

    # ── 写入路径 ───────────────────────────────────────
    def resolve_write(self, raw: str | None) -> Path:
        """解析写入路径；raw 为空 / 不传 → 用 settings.BACKUP_DIR 默认根目录"""
        settings = get_settings()
        target = raw if raw else settings.BACKUP_DIR
        p = Path(target).resolve()
        self._assert_within(p)
        return p

    # ── 读取路径 ───────────────────────────────────────
    def resolve_read(self, raw: str) -> Path:
        """解析读取路径（含文件存在性校验）"""
        if not raw:
            raise PathSecurityError("读取路径不能为空")
        p = Path(raw).resolve()
        self._assert_within(p)
        if not p.is_file():
            raise InvalidBackupFileError(f"文件不存在: {p}")
        return p

    # ── 上传路径（独立前缀，便于审计）───────────────
    def resolve_upload(self) -> Path:
        """上传 .sql 落地路径：BACKUP_DIR/_uploads/，自动创建目录"""
        settings = get_settings()
        upload_dir = Path(settings.BACKUP_DIR) / "_uploads"
        p = upload_dir.resolve()
        self._assert_within(p)
        p.mkdir(parents=True, exist_ok=True)
        return p

    # ── 内部 ──────────────────────────────────────────
    def _assert_within(self, p: Path) -> None:
        """p 必须落在 self._allowed_roots 之一下面"""
        for root in self._allowed_roots:
            try:
                p.relative_to(root)
                return
            except ValueError:
                continue
        raise PathSecurityError(f"路径不在白名单: {p}")

    @property
    def allowed_roots(self) -> list[Path]:
        """对外暴露的白名单根路径（只读）"""
        return list(self._allowed_roots)