"""备份记录 / 列表响应 DTO"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class BackupRecordDTO(BaseModel):
    """单条备份记录"""

    id: int
    name: str
    backup_type: Literal["full", "schema", "data"]
    scope: Literal["all", "partial"]
    tables: list[str]
    tables_count: int
    output_dir: str
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    row_count: int = 0
    progress: int = 0
    progress_msg: str = ""
    status: Literal["pending", "running", "success", "failed", "interrupted"]
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_by: int
    created_at: datetime


class BackupListResponse(BaseModel):
    """备份列表响应"""

    items: list[BackupRecordDTO]
    total: int
    page: int
    page_size: int


class RestoreRecordDTO(BaseModel):
    """单条恢复记录"""

    id: int
    name: str
    source_type: Literal["file", "upload", "history"]
    source_path: str
    source_backup_id: Optional[int] = None
    restore_mode: Literal["cover", "upsert"]
    tables: list[str] = []
    tables_count: int = 0
    pre_backup_id: Optional[int] = None
    progress: int = 0
    progress_msg: str = ""
    status: Literal["pending", "running", "success", "failed"]
    rows_inserted: int = 0
    rows_skipped: int = 0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_by: int
    created_at: datetime


class RestoreListResponse(BaseModel):
    """恢复列表响应"""

    items: list[RestoreRecordDTO]
    total: int
    page: int
    page_size: int