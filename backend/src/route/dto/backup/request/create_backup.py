"""创建备份请求 DTO"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class CreateBackupRequest(BaseModel):
    """创建备份请求体"""

    backup_type: Literal["full", "schema", "data"] = Field(
        "full", description="备份粒度：full=结构+数据 / schema=仅结构 / data=仅数据"
    )
    scope: Literal["all", "partial"] = Field(
        "all", description="备份范围：all=全表 / partial=选子集"
    )
    tables: Optional[list[str]] = Field(
        None, description="scope=partial 时必填；scope=all 时忽略"
    )
    output_dir: Optional[str] = Field(
        None, description="输出根目录；None=用 settings.BACKUP_DIR 默认"
    )
    name: Optional[str] = Field(
        None, max_length=120, description="文件名；None=自动生成"
    )

    @model_validator(mode="after")
    def _check(self):
        if self.scope == "partial" and not self.tables:
            raise ValueError("scope=partial 时必须提供 tables 列表")
        if self.tables and any("/" in t or "\\" in t for t in self.tables):
            raise ValueError("tables 不能含路径分隔符")
        return self