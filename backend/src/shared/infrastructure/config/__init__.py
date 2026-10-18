"""infrastructure.config

只导出 settings —— 业务 DI 工厂已迁到各 `contexts/<ctx>/infrastructure/di/`。
"""
from shared.infrastructure.config.settings import get_settings

__all__ = ["get_settings"]
