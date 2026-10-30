--
-- S3: attribution 库 —— collect_logs 表统一为新版结构（29 列）
--
-- 背景：
--   远端存在两张表：
--     · collect_logs（复数）= 旧结构（service_name/category/action/meta/total_count/...），50 行
--     · collect_log （单数）= 接近新版（task_id/facet/name/kind/mode/params_json/...），19 列 1 行
--   而本地代码（Python ORM / Java PO / postgres/initdb/02-collect-logs.sql）用的是新版 29 列结构。
--   → 两者都对不上，采集日志一条都写不进去。
--
-- 本脚本：
--   ① 归档旧表 collect_logs → collect_logs_legacy_20261029（保留 1 个月不删）
--   ② 建新版 collect_logs（29 列，含 duration_ms 与 5 个 CHECK 约束）
--   ③ 迁移旧 collect_logs 的 50 行（旧结构 → 新结构，字段映射见下）
--   ④ 迁移 collect_log（单数）的 1 行（缺列用默认值补，kind='' 按 mode='condition' 补成 'incremental'）
--   ⑤ 删除 collect_log（单数）
--
-- ⚠️ 执行前必须已备份：pg_dump -t collect_logs -t collect_log attribution > backup.sql
--
-- 执行：psql -h 8.148.204.54 -U zhouch -d attribution -f 03-rebuild-collect-logs.sql
--

BEGIN;

-- ═══════════════════════════════════════════════════════════════════════
-- ① 归档旧表
-- ═══════════════════════════════════════════════════════════════════════
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables
                WHERE table_schema='public' AND table_name='collect_logs')
       AND NOT EXISTS (SELECT 1 FROM information_schema.tables
                WHERE table_schema='public' AND table_name='collect_logs_legacy_20261029')
    THEN
        EXECUTE 'ALTER TABLE collect_logs RENAME TO collect_logs_legacy_20261029';
        RAISE NOTICE '旧表 collect_logs 已归档为 collect_logs_legacy_20261029';
    END IF;
END $$;

-- ═══════════════════════════════════════════════════════════════════════
-- ② 建新版 collect_logs（29 列）
-- ═══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.collect_logs (
    task_id         VARCHAR(64)  PRIMARY KEY,           -- hex，= Redis key collect:task:{id} 的 id
    facet           VARCHAR(32)  NOT NULL DEFAULT '',   -- 五分类：tech/capital/fundamental/news/sentiment
    name            VARCHAR(64)  NOT NULL DEFAULT '',   -- collector 名，如 daily_kline
    kind            VARCHAR(32)  NOT NULL DEFAULT '',   -- 采集方式：incremental/full
    mode            VARCHAR(16)  NOT NULL DEFAULT 'manual', -- 编排来源：manual/schedule
    trigger_source  VARCHAR(16)  NOT NULL DEFAULT 'manual', -- manual/schedule/api/retry
    trigger_user    VARCHAR(64),
    params_json     JSONB        NOT NULL DEFAULT '{}'::jsonb,
    range_start     DATE,
    range_end       DATE,
    status          VARCHAR(16)  NOT NULL DEFAULT 'queued',
    progress        SMALLINT     NOT NULL DEFAULT 0,
    total           INTEGER      NOT NULL DEFAULT 0,     -- 计划总步数（步数口径）
    done            INTEGER      NOT NULL DEFAULT 0,
    success         INTEGER      NOT NULL DEFAULT 0,
    fail            INTEGER      NOT NULL DEFAULT 0,
    skip            INTEGER      NOT NULL DEFAULT 0,
    saved_total     BIGINT       NOT NULL DEFAULT 0,     -- 实际落库行数（行数口径）
    message         TEXT,
    error           TEXT,
    detail          JSONB        NOT NULL DEFAULT '[]'::jsonb,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    duration_ms     INTEGER,
    cancel_requested BOOLEAN     NOT NULL DEFAULT FALSE,
    cancelled_at    TIMESTAMPTZ,
    parent_task_id  VARCHAR(64),

    CONSTRAINT ck_collect_logs_status
        CHECK (status IN ('queued','running','done','failed','cancelled')),
    CONSTRAINT ck_collect_logs_kind
        CHECK (kind IN ('', 'collect','incremental','full','realtime','both')),
    CONSTRAINT ck_collect_logs_mode
        CHECK (mode IN ('condition','full','schedule','manual')),
    CONSTRAINT ck_collect_logs_trigger_source
        CHECK (trigger_source IN ('manual','schedule','api','retry')),
    CONSTRAINT ck_collect_logs_counters
        CHECK (total >= 0 AND done >= 0 AND success >= 0 AND fail >= 0
               AND skip >= 0 AND saved_total >= 0),
    CONSTRAINT ck_collect_logs_done_le_total
        CHECK (done <= total OR total = 0)
);

COMMENT ON TABLE  public.collect_logs IS '采集任务日志：一行 = 一次采集任务（Collector 写，Java 只读）';
COMMENT ON COLUMN public.collect_logs.task_id IS '任务 ID（hex，Collector 生成，两端一致的关联键）';
COMMENT ON COLUMN public.collect_logs.facet IS '五分类数据面：tech/capital/fundamental/news/sentiment';
COMMENT ON COLUMN public.collect_logs.name IS 'service 名（= collector 的 name 属性，日志关联键）';
COMMENT ON COLUMN public.collect_logs.kind IS '采集方式（本次执行）：incremental/full';
COMMENT ON COLUMN public.collect_logs.mode IS '编排来源：manual/schedule';
COMMENT ON COLUMN public.collect_logs.total IS '计划总步数（步数口径，不是行数）';
COMMENT ON COLUMN public.collect_logs.saved_total IS '实际落库行数（行数口径，唯一非步数字段）';
COMMENT ON COLUMN public.collect_logs.detail IS '每步明细 JSONB 数组（排查用）';
COMMENT ON COLUMN public.collect_logs.parent_task_id IS '续跑/重试时指向原任务';

-- ═══════════════════════════════════════════════════════════════════════
-- ③ 迁移旧 collect_logs（复数，旧结构 50 行）
--    kind: action ∈ {incremental, full_refresh} → {incremental, full}
-- ═══════════════════════════════════════════════════════════════════════
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables
                WHERE table_schema='public' AND table_name='collect_logs_legacy_20261029')
       AND NOT EXISTS (SELECT 1 FROM information_schema.tables
                WHERE table_schema='public' AND table_name='collect_log')
    THEN
        INSERT INTO public.collect_logs (
            task_id, facet, name, kind, mode, trigger_source, trigger_user,
            params_json, range_start, range_end, status, progress,
            total, done, success, fail, skip, saved_total,
            message, error, detail,
            created_at, started_at, finished_at, updated_at, duration_ms,
            cancel_requested, cancelled_at, parent_task_id
        )
        SELECT
            gen_random_uuid()::text,
            COALESCE(category, ''),
            COALESCE(service_name, ''),
            CASE action
                WHEN 'full_refresh' THEN 'full'
                WHEN 'collect'      THEN 'collect'
                WHEN 'both'         THEN 'both'
                WHEN 'realtime'     THEN 'realtime'
                WHEN 'incremental'  THEN 'incremental'
                WHEN 'full'         THEN 'full'
                ELSE ''
            END,
            'manual',
            CASE trigger_source
                WHEN 'manual'   THEN 'manual'
                WHEN 'schedule' THEN 'schedule'
                WHEN 'api'      THEN 'api'
                WHEN 'retry'    THEN 'retry'
                ELSE 'manual'
            END,
            trigger_user,
            COALESCE(meta, '{}'::jsonb),
            NULLIF(meta->>'start_date', '')::date,
            NULLIF(meta->>'end_date', '')::date,
            CASE status
                WHEN 'queued'   THEN 'queued'
                WHEN 'running'  THEN 'running'
                WHEN 'done'     THEN 'done'
                WHEN 'failed'   THEN 'failed'
                WHEN 'cancelled' THEN 'cancelled'
                ELSE 'queued'
            END,
            COALESCE(progress, 0),
            COALESCE(total_count, 0),
            COALESCE(total_count, 0),
            GREATEST(COALESCE(total_count, 0) - COALESCE(fail_count, 0), 0),
            COALESCE(fail_count, 0),
            0,
            COALESCE(saved_count, 0),
            NULL,
            error_message,
            '[]'::jsonb,
            created_at,
            started_at,
            finished_at,
            updated_at,
            duration_ms,
            FALSE,
            NULL,
            NULL
        FROM public.collect_logs_legacy_20261029;
        RAISE NOTICE '旧 collect_logs 数据已迁移';
    END IF;
END $$;

-- ═══════════════════════════════════════════════════════════════════════
-- ④ 迁移 collect_log（单数，19 列 1 行）—— 缺列补默认值
--    kind='' 且 mode='condition' → 'incremental'
-- ═══════════════════════════════════════════════════════════════════════
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables
                WHERE table_schema='public' AND table_name='collect_log')
    THEN
        INSERT INTO public.collect_logs (
            task_id, facet, name, kind, mode, trigger_source, trigger_user,
            params_json, range_start, range_end, status, progress,
            total, done, success, fail, skip, saved_total,
            message, error, detail,
            created_at, started_at, finished_at, updated_at, duration_ms,
            cancel_requested, cancelled_at, parent_task_id
        )
        SELECT
            task_id,
            COALESCE(facet, ''),
            COALESCE(name, ''),
            CASE
                WHEN COALESCE(kind, '') <> '' THEN kind
                WHEN mode = 'condition'        THEN 'incremental'
                WHEN mode = 'full'             THEN 'full'
                ELSE 'incremental'
            END,
            'manual',
            'manual',
            NULL,
            COALESCE(params_json, '{}'::jsonb),
            range_start,
            range_end,
            CASE status
                WHEN 'queued'    THEN 'queued'
                WHEN 'running'   THEN 'running'
                WHEN 'done'      THEN 'done'
                WHEN 'failed'    THEN 'failed'
                WHEN 'cancelled' THEN 'cancelled'
                ELSE 'queued'
            END,
            0,
            COALESCE(total, 0),
            COALESCE(total, 0),
            COALESCE(total, 0),
            0,
            0,
            COALESCE(saved_total, 0),
            message,
            NULL,
            '[]'::jsonb,
            created_at,
            started_at,
            finished_at,
            updated_at,
            NULL,
            FALSE,
            NULL,
            NULL
        FROM public.collect_log
        WHERE NOT EXISTS (
            SELECT 1 FROM public.collect_logs c WHERE c.task_id = collect_log.task_id
        );
        RAISE NOTICE 'collect_log（单数）数据已迁移';

        -- ⑤ 删除单数表
        DROP TABLE public.collect_log;
        RAISE NOTICE 'collect_log（单数）已删除';
    END IF;
END $$;

-- ═══════════════════════════════════════════════════════════════════════
-- 索引
-- ═══════════════════════════════════════════════════════════════════════
CREATE INDEX IF NOT EXISTS ix_collect_logs_name_status
    ON public.collect_logs (name, status);
CREATE INDEX IF NOT EXISTS ix_collect_logs_facet
    ON public.collect_logs (facet);
CREATE INDEX IF NOT EXISTS ix_collect_logs_created
    ON public.collect_logs (created_at DESC);
CREATE INDEX IF NOT EXISTS ix_collect_logs_status_created
    ON public.collect_logs (status, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_collect_logs_trigger_source
    ON public.collect_logs (trigger_source, created_at DESC);

COMMIT;

-- 校验
-- SELECT count(*) FROM information_schema.columns WHERE table_name='collect_logs';        -- 期望 29
-- SELECT count(*) FROM collect_logs;                                                        -- 期望 51
-- SELECT count(*) FROM information_schema.tables
--  WHERE table_name IN ('collect_log','collect_logs_legacy_20261029');                       -- 期望 1
