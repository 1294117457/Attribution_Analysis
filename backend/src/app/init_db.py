"""init_db — 自动建表工具（Phase 2 修复）

问题：
    collect_logs 表是 v2 新增的，但项目里没有任何 create_all 调用，
    导致 backend 启动后 GET /collect/logs/* 直接报 UndefinedTableError。

解决：
    启动时（lifespan 内）自动调用 AttribBase.metadata.create_all()，
    对所有 AttribBase 子类建表（幂等，已存在的表不重建）。

用法（在 main.py lifespan 内）：
    from app.init_db import ensure_attrib_tables
    await ensure_attrib_tables()

也可以直接命令行执行：
    python -m app.init_db
"""
from __future__ import annotations

import logging
import pkgutil
from typing import Iterable

from sqlalchemy.ext.asyncio import AsyncEngine

from shared.infrastructure.connection.db_factory import db_async_engine
from shared.infrastructure.persistence.orm_base import AttribBase

logger = logging.getLogger(__name__)


# 显式 import 列表（Phase 2 修复：确保 collect_log 被注册）
# 新增 ORM 时记得在这里加 import
_REQUIRED_MODEL_IMPORTS = (
    "contexts.collect.infrastructure.persistence.models.collect_log",
)


def _import_required_models() -> None:
    """强制 import 所有 AttribBase 子类 ORM（让 metadata 加载）"""
    for module_path in _REQUIRED_MODEL_IMPORTS:
        try:
            __import__(module_path)
        except ImportError as e:
            logger.warning("[init_db] 无法 import %s: %s", module_path, e)


def _list_attrib_subclasses() -> Iterable[type]:
    """枚举所有 AttribBase 已知子类（用于诊断）"""
    seen: set[type] = set()

    def _walk(cls):
        for sub in cls.__subclasses__():
            if sub in seen:
                continue
            seen.add(sub)
            yield sub
            yield from _walk(sub)

    return list(_walk(AttribBase))


async def ensure_attrib_tables(engine: AsyncEngine | None = None) -> None:
    """确保所有 AttribBase 子类对应的表都存在（幂等）

    - 已存在的表：跳过
    - 不存在的表：CREATE TABLE

    Args:
        engine: 可选，注入 engine（测试用）。默认用 db_async_engine（业务库）。
    """
    if engine is None:
        engine = db_async_engine

    # 1. 强制 import ORM（让 metadata 加载）
    _import_required_models()

    # 2. 列出已注册表
    tables = sorted(AttribBase.metadata.tables.keys())
    logger.info("[init_db] AttribBase 注册表数: %d", len(tables))
    for t in tables:
        logger.info("[init_db]   - %s", t)

    if not tables:
        logger.warning(
            "[init_db] ⚠️ 没有 AttribBase 子类被注册，"
            "跳过 create_all（请检查 _REQUIRED_MODEL_IMPORTS）"
        )
        return

    # 3. create_all（幂等）
    async with engine.begin() as conn:
        await conn.run_sync(AttribBase.metadata.create_all)

    # 4. 验证：实际查 DB
    from sqlalchemy import text
    async with engine.connect() as conn:
        placeholders = ",".join(f":t{i}" for i in range(len(tables)))
        sql = (
            f"SELECT tablename FROM pg_tables "
            f"WHERE schemaname='public' AND tablename IN ({placeholders})"
        )
        params = {f"t{i}": t for i, t in enumerate(tables)}
        result = await conn.execute(text(sql), params)
        existing = {row[0] for row in result.fetchall()}

    missing = set(tables) - existing
    if missing:
        logger.warning(
            "[init_db] ⚠️ create_all 失败，仍缺表: %s（可能用户没 DDL 权限）",
            missing,
        )
        logger.warning(
            "[init_db] 请手动执行: psql ... -f backend/sql/migrate_collect_logs.sql"
        )
    else:
        logger.info("[init_db] ✅ 所有 %d 张 AttribBase 表已就绪", len(tables))


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    )
    asyncio.run(ensure_attrib_tables())
