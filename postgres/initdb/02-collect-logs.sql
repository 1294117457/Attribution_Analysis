--
-- 采集任务日志表 collect_logs 建表脚本
--
-- 执行：psql -U <user> -d attribution -f scripts/migrate_collect_logs.sql
--
-- 范围：
--   1) 建 collect_logs 表（attribution 业务库）
--   2) 建 5 个查询索引
--   3) 归档并删除旧表 collect_logs（若存在旧结构）
--
-- 说明：
--   - 表由迁移脚本一次性创建，Collector 与 Java 都不在运行时建表
--   - 旧表 collect_logs（结构不同）先 RENAME 留档，1 个月后再 DROP
--   - 所有时间字段用 timestamptz（跨时区部署后语义不漂移）
--

BEGIN;

-- ═══════════════════════════════════════════════════════════════════════════
-- 0) 归档旧表（若存在旧结构）
-- ═══════════════════════════════════════════════════════════════════════════

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'collect_logs'
    ) AND NOT EXISTS (
        -- 已是新结构（含 progress 列）→ 不归档，避免重复执行时误改名
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'collect_logs'
          AND column_name = 'progress'
    ) THEN
        -- 旧表结构与新表不同（id uuid / service_name / category / action /
        -- trigger_source+trigger_user / meta jsonb / total_count / saved_count /
        -- fail_count / progress / error_message / duration_ms），无法原地改列。
        -- 旧数据仅数十行且多为 failed/running 残留，无归档价值，仅留档 1 个月。
        EXECUTE 'ALTER TABLE collect_logs RENAME TO collect_logs_legacy_' || to_char(now(), 'YYYYMMDD');
        RAISE NOTICE '旧表 collect_logs 已归档为 collect_logs_legacy_%', to_char(now(), 'YYYYMMDD');
    END IF;
END $$;

-- ═══════════════════════════════════════════════════════════════════════════
-- 1) 建 collect_logs 表
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS collect_logs (
    -- ── 身份与定位 ──────────────────────────────────────
    task_id       VARCHAR(64)  PRIMARY KEY,          -- hex，= Redis key collect:task:{id} 的 id
    facet         VARCHAR(32)  NOT NULL DEFAULT '',  -- 五分类：tech/capital/fundamental/news/sentiment
    name          VARCHAR(64)  NOT NULL DEFAULT '',  -- collector 名，如 daily_kline
    -- ★ kind 列承载「本次执行的采集方式」：incremental（增量）/ full（全量覆盖）
    --   （零 DDL 迁移：ck_collect_logs_kind 本就允许这两个值）
    kind          VARCHAR(32)  NOT NULL DEFAULT '',
    -- ★ mode 列语义收敛为「编排来源」：manual / schedule
    mode          VARCHAR(16)  NOT NULL DEFAULT 'manual',

    -- ── 触发来源（审计）────────────────────────────────
    trigger_source VARCHAR(16) NOT NULL DEFAULT 'manual', -- manual/schedule/api/retry
    trigger_user   VARCHAR(64),                        -- 手动触发人（schedule/api 时为 NULL）

    -- ── 采集参数（审计）────────────────────────────────
    params_json    JSONB         NOT NULL DEFAULT '{}'::jsonb,  -- 原始请求参数
    range_start    DATE,                                -- 采集时间范围起
    range_end      DATE,                                -- 采集时间范围止

    -- ── 状态机 ────────────────────────────────────────
    status         VARCHAR(16)  NOT NULL DEFAULT 'queued',
                   -- queued → running → done | failed | cancelled
    progress       SMALLINT     NOT NULL DEFAULT 0,     -- 0-100，供列表快速渲染

    -- ── 计数器（步数口径：一次 collect() 调用 = 1 步）──
    total          INTEGER      NOT NULL DEFAULT 0,     -- 计划总步数
    done           INTEGER      NOT NULL DEFAULT 0,     -- 已完成步数
    success        INTEGER      NOT NULL DEFAULT 0,     -- 成功步数
    fail           INTEGER      NOT NULL DEFAULT 0,     -- 失败步数
    skip           INTEGER      NOT NULL DEFAULT 0,     -- 跳过步数（无数据/已存在）

    -- ── 计数器（行数口径：写入 raw_data 的行）──────────
    saved_total    BIGINT       NOT NULL DEFAULT 0,     -- 实际落库行数

    -- ── 结果信息 ──────────────────────────────────────
    message        TEXT,                                -- 终态摘要（≤800 字符）
    error          TEXT,                                -- 异常堆栈/错误详情（仅 failed/cancelled）
    detail         JSONB        NOT NULL DEFAULT '[]'::jsonb, -- 每步明细（可选，排查用）

    -- ── 时间（全部 timestamptz）───────────────────────
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),  -- 建任务时刻
    started_at     TIMESTAMPTZ,                          -- 开始执行
    finished_at    TIMESTAMPTZ,                          -- 到达终态
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),  -- 最后一次写入
    duration_ms    INTEGER,                              -- finished_at - started_at

    -- ── 中断支持 ─────────────────────────────────────
    cancel_requested BOOLEAN     NOT NULL DEFAULT FALSE,-- 是否收到过中断请求
    cancelled_at     TIMESTAMPTZ,                         -- 实际中断时刻
    parent_task_id   VARCHAR(64),                        -- 续跑/重试时指向原任务

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

COMMENT ON TABLE  collect_logs IS '采集任务日志：一行 = 一次采集任务（Collector 写，Java 只读）';
COMMENT ON COLUMN collect_logs.task_id IS '任务 ID（hex，Collector 生成，两端一致的关联键）';
COMMENT ON COLUMN collect_logs.kind IS '采集方式（本次执行）：incremental/full（零 DDL 迁移，沿用 kind 列）';
COMMENT ON COLUMN collect_logs.mode IS '编排来源：manual/schedule';
COMMENT ON COLUMN collect_logs.total IS '计划总步数（步数口径，不是行数）';
COMMENT ON COLUMN collect_logs.saved_total IS '实际落库行数（行数口径，唯一非步数字段）';
COMMENT ON COLUMN collect_logs.detail IS '每步明细 JSONB 数组（排查用）';
COMMENT ON COLUMN collect_logs.parent_task_id IS '续跑/重试时指向原任务';

-- ═══════════════════════════════════════════════════════════════════════════
-- 2) 查询索引
-- ═══════════════════════════════════════════════════════════════════════════

-- 按 service + 状态筛选（历史页主查询）
CREATE INDEX IF NOT EXISTS ix_collect_logs_name_status
    ON collect_logs (name, status);
-- 按 facet 筛选
CREATE INDEX IF NOT EXISTS ix_collect_logs_facet
    ON collect_logs (facet);
-- 按时间倒序（历史页默认排序）
CREATE INDEX IF NOT EXISTS ix_collect_logs_created
    ON collect_logs (created_at DESC);
-- 查「进行中」的任务（重启恢复用）
CREATE INDEX IF NOT EXISTS ix_collect_logs_status_created
    ON collect_logs (status, created_at DESC);
-- 查定时触发来源的任务
CREATE INDEX IF NOT EXISTS ix_collect_logs_trigger_source
    ON collect_logs (trigger_source, created_at DESC);

COMMIT;

-- ═══════════════════════════════════════════════════════════════════════════
-- 验证
-- ═══════════════════════════════════════════════════════════════════════════
-- SELECT table_name, column_name, data_type FROM information_schema.columns
--   WHERE table_name = 'collect_logs' ORDER BY ordinal_position;
-- SELECT indexname FROM pg_indexes WHERE tablename = 'collect_logs';
