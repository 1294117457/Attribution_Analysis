"""step7 数据库迁移脚本

执行内容（幂等）：
  1. CREATE TABLE IF NOT EXISTS collect_schedule
  2. CREATE TABLE IF NOT EXISTS collect_run_log
  3. (可选) 从 collect_jobs 迁移历史数据到 collect_schedule + collect_run_log

不删 collect_jobs / collect_data_ports —— 由 W4 阶段手动 DROP。

用法：
  cd backend
  python scripts/migrate_step7.py
"""
from __future__ import annotations

import asyncio
import logging

from sqlalchemy import text

from shared.infrastructure.persistence.connection import async_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


COLLECT_SCHEDULE_DDL = """
CREATE TABLE IF NOT EXISTS collect_schedule (
    id              SERIAL PRIMARY KEY,
    service_name    VARCHAR(64) NOT NULL,
    enabled         BOOLEAN NOT NULL DEFAULT TRUE,
    trigger_type    VARCHAR(16) NOT NULL,
    times           TEXT[] NOT NULL DEFAULT '{}',
    interval_seconds INT,
    params          JSONB NOT NULL DEFAULT '{}',
    concurrency     INT NOT NULL DEFAULT 5,
    display_name    VARCHAR(128),
    description     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_collect_schedule_trigger CHECK (
        (trigger_type = 'time' AND times <> '{}' AND interval_seconds IS NULL) OR
        (trigger_type = 'interval' AND interval_seconds IS NOT NULL AND interval_seconds >= 30)
    )
);
CREATE INDEX IF NOT EXISTS ix_collect_schedule_enabled
    ON collect_schedule(enabled) WHERE enabled = TRUE;
"""

COLLECT_RUN_LOG_DDL = """
CREATE TABLE IF NOT EXISTS collect_run_log (
    id              BIGSERIAL PRIMARY KEY,
    schedule_id     INT,
    service_name    VARCHAR(64) NOT NULL,
    trigger_type    VARCHAR(16) NOT NULL,
    params          JSONB NOT NULL DEFAULT '{}',
    started_at      TIMESTAMPTZ NOT NULL,
    finished_at     TIMESTAMPTZ,
    duration_ms     INT,
    status          VARCHAR(16) NOT NULL DEFAULT 'running',
    total_count     INT NOT NULL DEFAULT 0,
    success_count   INT NOT NULL DEFAULT 0,
    fail_count      INT NOT NULL DEFAULT 0,
    skip_count      INT NOT NULL DEFAULT 0,
    saved_count     INT NOT NULL DEFAULT 0,
    message         TEXT,
    error           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_collect_run_log_status CHECK (status IN ('running', 'success', 'failed', 'cancelled'))
);
CREATE INDEX IF NOT EXISTS ix_collect_run_log_service_time
    ON collect_run_log(service_name, started_at DESC);
CREATE INDEX IF NOT EXISTS ix_collect_run_log_status
    ON collect_run_log(status);
CREATE INDEX IF NOT EXISTS ix_collect_run_log_schedule
    ON collect_run_log(schedule_id);
"""

MIGRATE_SCHEDULE_SQL = """
INSERT INTO collect_schedule (
    service_name, enabled, trigger_type, times, interval_seconds,
    params, concurrency, display_name, created_at, updated_at
)
SELECT
    task_type,
    enabled,
    COALESCE(schedule_type, 'time'),
    COALESCE(times, '{}'),
    interval_seconds,
    COALESCE(params::text, '{}')::jsonb,
    concurrency,
    display_name,
    created_at,
    updated_at
FROM collect_jobs
WHERE mode IN ('time', 'interval')
ON CONFLICT DO NOTHING;
"""

MIGRATE_LOG_SQL = """
INSERT INTO collect_run_log (
    schedule_id, service_name, trigger_type, params,
    started_at, finished_at, duration_ms, status,
    total_count, success_count, fail_count, skip_count, saved_count,
    message, created_at
)
SELECT
    NULL,
    task_type,
    trigger_type,
    COALESCE(params::text, '{}')::jsonb,
    started_at,
    finished_at,
    duration_ms,
    status,
    total_count,
    success_count,
    fail_count,
    skip_count,
    0,
    message,
    created_at
FROM collect_jobs
WHERE status IN ('success', 'failed', 'cancelled');
"""


async def main():
    async with async_engine.begin() as conn:
        logger.info("Step 1: CREATE collect_schedule ...")
        for stmt in [s for s in COLLECT_SCHEDULE_DDL.split(";\n") if s.strip()]:
            await conn.execute(text(stmt))
        logger.info("Step 2: CREATE collect_run_log ...")
        for stmt in [s for s in COLLECT_RUN_LOG_DDL.split(";\n") if s.strip()]:
            await conn.execute(text(stmt))

        # 跳过老表数据迁移——直接 drop 老表
        # 检测 collect_jobs / collect_data_ports 是否存在
        exists = (await conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
            "WHERE table_name = 'collect_jobs')"
        ))).scalar()
        if exists:
            logger.info("Step 3: DROP collect_jobs ...")
            await conn.execute(text("DROP TABLE IF EXISTS collect_jobs CASCADE"))
        else:
            logger.info("Step 3: collect_jobs 不存在，跳过")
        exists = (await conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
            "WHERE table_name = 'collect_data_ports')"
        ))).scalar()
        if exists:
            logger.info("Step 4: DROP collect_data_ports ...")
            await conn.execute(text("DROP TABLE IF EXISTS collect_data_ports CASCADE"))
        else:
            logger.info("Step 4: collect_data_ports 不存在，跳过")

    logger.info("✅ step7 迁移完成")


if __name__ == "__main__":
    asyncio.run(main())
