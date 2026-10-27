-- migrate_collect_logs.sql
-- Phase 2 修复：手动建表（如果不想依赖启动时自动建表，可手动执行此脚本）
--
-- 用法：
--   psql -h localhost -U postgres -d attribution -f backend/sql/migrate_collect_logs.sql
--
-- 幂等：IF NOT EXISTS，已存在的表不重建
-- 对应 ORM：backend/src/shared/infrastructure/persistence/models/collect_log.py
--
-- ⚠️ 已有表的状态机迁移（2026-10-26）：
--    status 默认值 pending → init。已有表用 ALTER 改默认值即可，
--    历史数据的 status 值（pending/running/...）保持不变，前端仍能正常显示。

CREATE TABLE IF NOT EXISTS public.collect_logs (
    id              UUID PRIMARY KEY,
    service_name    VARCHAR(128) NOT NULL,
    category        VARCHAR(64)  NOT NULL,
    action          VARCHAR(32)  NOT NULL,
    trigger_source  VARCHAR(32)  NOT NULL DEFAULT 'manual',
    trigger_user    VARCHAR(64),
    meta            JSONB        NOT NULL DEFAULT '{}'::jsonb,
    status          VARCHAR(32)  NOT NULL DEFAULT 'init',
    total_count     INTEGER      NOT NULL DEFAULT 0,
    saved_count     INTEGER      NOT NULL DEFAULT 0,
    fail_count      INTEGER      NOT NULL DEFAULT 0,
    progress        INTEGER      NOT NULL DEFAULT 0,
    duration_ms     INTEGER,
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

-- 已有表的迁移（2026-10-26）：status 默认值 pending → init
-- （历史行的 status 值不动，前端已兼容展示）
ALTER TABLE public.collect_logs
    ALTER COLUMN status SET DEFAULT 'init';

-- ═══════════════════════════════════════════════════════════════════
-- 通用化迁移（2026-10-26）：采集专用字段 → 通用操作日志字段
--
--   facet  → category   分组维度（采集时 tech/capital/...）
--   kind   → action     动作类型（采集时 incremental/full_refresh/...）
--   params → meta       动态上下文 JSONB（采集时存原始入参）
--
-- ⚠️ RENAME COLUMN 会保留数据（只改列名，不丢值）。
--    已存在的表必须执行这段，否则 ORM 找不到 category/action/meta 列。
--    新建的表（上面的 CREATE TABLE）已经是新列名，这段会报错但可忽略。
-- ═══════════════════════════════════════════════════════════════════

DO $$
BEGIN
    -- facet → category
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'collect_logs'
          AND column_name = 'facet'
    ) THEN
        ALTER TABLE public.collect_logs RENAME COLUMN facet TO category;
        RAISE NOTICE '已重命名 collect_logs.facet → category';
    END IF;

    -- kind → action
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'collect_logs'
          AND column_name = 'kind'
    ) THEN
        ALTER TABLE public.collect_logs RENAME COLUMN kind TO action;
        RAISE NOTICE '已重命名 collect_logs.kind → action';
    END IF;

    -- params → meta
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'collect_logs'
          AND column_name = 'params'
    ) THEN
        ALTER TABLE public.collect_logs RENAME COLUMN params TO meta;
        RAISE NOTICE '已重命名 collect_logs.params → meta';
    END IF;
END
$$;

-- 补 duration_ms 列（通用耗时字段；已存在则跳过）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'collect_logs'
          AND column_name = 'duration_ms'
    ) THEN
        ALTER TABLE public.collect_logs ADD COLUMN duration_ms INTEGER;
        RAISE NOTICE '已添加 collect_logs.duration_ms';
    END IF;
END
$$;

-- 验证
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size('public.' || tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public' AND tablename = 'collect_logs';

-- 列清单自检（应含 category / action / meta / duration_ms，不含 facet/kind/params）
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'collect_logs'
ORDER BY ordinal_position;
