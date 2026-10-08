"""更新备份配置请求 DTO"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class UpdateConfigRequest(BaseModel):
    """更新备份配置

    v1 简化：只写日志，不持久化；重启后回退到 settings 默认值。
    路径白名单仍要做（PathResolver.assert_str_against_root）。
    """

    default_output_dir: Optional[str] = Field(
        None, description="默认输出目录"
    )
    allowed_roots: Optional[list[str]] = Field(
        None, description="允许的根路径列表"
    )