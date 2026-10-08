"""恢复请求 DTO"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class RestoreRequest(BaseModel):
    """恢复请求体"""

    source_type: Literal["history", "upload", "file"] = Field(
        ..., description="来源类型：history=从历史选 / upload=前端上传 / file=服务端路径"
    )
    source_backup_id: Optional[int] = Field(
        None, description="source_type=history 时必填"
    )
    upload_id: Optional[str] = Field(
        None, description="source_type=upload 时必填（upload 接口返回）"
    )
    source_path: Optional[str] = Field(
        None, description="source_type=file 时必填（服务端绝对路径）"
    )
    restore_mode: Literal["cover", "upsert"] = Field(
        "cover", description="恢复模式：cover=全量覆盖 / upsert=增量"
    )
    confirm: bool = Field(
        False, description="必须显式置 True，服务端做强校验"
    )

    @model_validator(mode="after")
    def _check(self):
        if not self.confirm:
            raise ValueError("恢复操作必须 confirm=True（破坏性操作）")
        if self.source_type == "history" and not self.source_backup_id:
            raise ValueError("source_type=history 时必须提供 source_backup_id")
        if self.source_type == "upload" and not self.upload_id:
            raise ValueError("source_type=upload 时必须提供 upload_id")
        if self.source_type == "file" and not self.source_path:
            raise ValueError("source_type=file 时必须提供 source_path")
        return self