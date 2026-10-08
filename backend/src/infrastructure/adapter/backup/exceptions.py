"""Backup 模块自定义异常

层级：
    BackupError
    ├── PathSecurityError         路径不在白名单 / 含禁止字符 / 越界
    ├── InvalidBackupFileError    备份文件格式错误（不是合法 SQL / 缺少头部 / 非本系统生成）
    └── BackupTaskRunningError    已有任务在跑（防并发）
"""

from __future__ import annotations


class BackupError(Exception):
    """所有 backup 模块异常的基类"""

    def __init__(self, message: str = "") -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return self.message or self.__class__.__name__


class PathSecurityError(BackupError):
    """路径不在白名单 / 含禁止字符 / 越界"""


class InvalidBackupFileError(BackupError):
    """备份文件格式错误（不是合法 SQL / 缺少头部 / 非本系统生成）"""


class BackupTaskRunningError(BackupError):
    """已有任务在跑（防并发：同时只允许 1 个 backup）"""