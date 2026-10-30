--
-- S3b: attribution 库 —— 补迁旧 collect_logs 的 50 行
--
-- ⚠️ S3 里这段迁移被错误地跳过了：
--    原脚本的守卫条件是 `EXISTS(collect_logs_legacy_*) AND NOT EXISTS(collect_log)`，
--    但执行到该段时 `collect_log`（单数）尚未被删除（它在后面的 ⑤ 才 DROP），
--    → 条件恒为 false → 50 行旧数据没迁过去。
--    本脚本补做这一步。
--
-- 执行：psql -h 8.148.204.54 -U zhouch -d attribution -f 03b-migrate-legacy-rows.sql
--

BEGIN;

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
        WHEN 'queued'    THEN 'queued'
        WHEN 'running'   THEN 'running'
        WHEN 'done'      THEN 'done'
        WHEN 'failed'    THEN 'failed'
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
FROM public.collect_logs_legacy_20261029 l
WHERE NOT EXISTS (
    SELECT 1 FROM public.collect_logs c
    WHERE c.name = COALESCE(l.service_name, '')
      AND c.created_at = l.created_at
      AND c.started_at IS NOT DISTINCT FROM l.started_at
);

COMMIT;

-- 校验：期望 51（50 旧 + 1 从 collect_log 单数表迁来的）
-- SELECT count(*) FROM collect_logs;
-- SELECT kind, count(*) FROM collect_logs GROUP BY 1 ORDER BY 1;
