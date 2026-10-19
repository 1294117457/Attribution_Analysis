-- migrate_collect_logs.sql
-- Phase 2 修复：手动建表（如果不想依赖启动时自动建表，可手动执行此脚本）
--
-- 用法：
--   psql -h localhost -U postgres -d attribution -f backend/sql/migrate_collect_logs.sql
--
-- 幂等：IF NOT EXISTS，已存在的表不重建
-- 对应 ORM：backend/src/contexts/collect/infrastructure/persistence/models/collect_log.py

CREATE TABLE IF NOT EXISTS public.collect_logs (
    id              UUID PRIMARY KEY,
    service_name    VARCHAR(128) NOT NULL,
    facet           VARCHAR(64)  NOT NULL,
    kind            VARCHAR(32)  NOT NULL,
    trigger_source  VARCHAR(32)  NOT NULL DEFAULT 'manual',
    trigger_user    VARCHAR(64),
    params          JSONB        NOT NULL DEFAULT '{}'::jsonb,
    status          VARCHAR(32)  NOT NULL DEFAULT 'pending',
    total_count     INTEGER      NOT NULL DEFAULT 0,
    saved_count     INTEGER      NOT NULL DEFAULT 0,
    fail_count      INTEGER      NOT NULL DEFAULT 0,
    progress        INTEGER      NOT NULL DEFAULT 0,
    error_message   TEXT,
    started_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMP WITH TIME ZONE,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 索引（与 ORM 一致）
CREATE INDEX IF NOT EXISTS idx_collect_logs_service_name
    ON public.collect_logs (service_name);

CREATE INDEX IF NOT EXISTS idx_collect_logs_status
    ON public.collect_logs (status);

CREATE INDEX IF NOT EXISTS idx_collect_logs_started_at
    ON public.collect_logs (started_at DESC);

CREATE INDEX IF NOT EXISTS idx_collect_logs_service_time
    ON public.collect_logs (service_name, started_at DESC);

-- 验证
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size('public.' || tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public' AND tablename = 'collect_logs';
