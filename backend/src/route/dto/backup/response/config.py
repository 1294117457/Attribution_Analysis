"""备份配置响应 DTO"""

from __future__ import annotations

from pydantic import BaseModel, Field


class BackupConfigDTO(BaseModel):
    """备份配置（GET /backups/config）"""

    default_output_dir: str = Field(..., description="默认输出目录")
    allowed_roots: list[str] = Field(..., description="允许的根路径列表")
    schema_version: int = Field(..., description="备份 schema 版本")
    max_file_size: int = Field(..., description="单文件最大大小（字节）")


class UploadBackupResponse(BaseModel):
    """上传 .sql 文件响应"""

    upload_id: str = Field(..., description="upload_id（传给 RestoreRequest）")
    filename: str
    size: int
    header: dict = Field(default_factory=dict, description="备份文件头部解析结果")