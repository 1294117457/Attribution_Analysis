-- =============================================================================
-- 006_backup_records.sql
-- 数据备份与导入功能 - 2 张表
--   sys_backup_records   备份任务全生命周期
--   sys_restore_records  恢复任务全生命周期
-- 幂等：所有语句用 IF NOT EXISTS
-- 由 main.py lifespan 中 _migrate_auth_system() 加载执行
-- 关联文档: docs/dev/step4/01数据备份/00-总体概要.md
-- =============================================================================

-- ── 1. sys_backup_records ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sys_backup_records (
    id              BIGSERIAL    PRIMARY KEY,
    name            VARCHAR(128) NOT NULL,                       -- 文件名: full_20261006_153000_abc123.sql
    backup_type     VARCHAR(16)  NOT NULL,                       -- full | schema | data
    scope           VARCHAR(16)  NOT NULL,                       -- all | partial
    tables          JSONB        NOT NULL DEFAULT '[]'::jsonb,   -- 备份的表名列表（all 时存全表名快照）
    tables_count    INTEGER      NOT NULL DEFAULT 0,
    output_dir      TEXT         NOT NULL,                       -- 实际输出目录（已 resolve 绝对路径）
    file_path       TEXT,                                        -- 实际产物绝对路径（成功后填）
    file_size       BIGINT,                                      -- 字节
    row_count       BIGINT       NOT NULL DEFAULT 0,
    progress        INTEGER      NOT NULL DEFAULT 0,             -- 0-100
    progress_msg    VARCHAR(255) NOT NULL DEFAULT '',            -- 当前阶段文案
    status          VARCHAR(16)  NOT NULL DEFAULT 'pending',     -- pending | running | success | failed | interrupted
    error_message   TEXT,
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    created_by      INTEGER      NOT NULL,                       -- user_id（来自 sys_users）
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_sys_backup_records_status     ON sys_backup_records (status);
CREATE INDEX IF NOT EXISTS ix_sys_backup_records_created_by ON sys_backup_records (created_by);
CREATE INDEX IF NOT EXISTS ix_sys_backup_records_created_at ON sys_backup_records (created_at DESC);

COMMENT ON TABLE  sys_backup_records                       IS '备份任务记录：一次备份 = 一行';
COMMENT ON COLUMN sys_backup_records.backup_type           IS 'full=结构+数据 / schema=仅结构 / data=仅数据';
COMMENT ON COLUMN sys_backup_records.scope                 IS 'all=全表 / partial=用户选了子集';
COMMENT ON COLUMN sys_backup_records.tables                IS '备份的表名列表（all 时存全表名快照，便于审计）';
COMMENT ON COLUMN sys_backup_records.status                IS 'pending=排队 / running=执行中 / success=成功 / failed=失败 / interrupted=被中断';

-- ── 2. sys_restore_records ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sys_restore_records (
    id                  BIGSERIAL    PRIMARY KEY,
    name                VARCHAR(128) NOT NULL,                   -- 任务名
    source_type         VARCHAR(16)  NOT NULL,                   -- file | upload | history
    source_path         TEXT         NOT NULL,                   -- 实际文件绝对路径
    source_backup_id    BIGINT,                                  -- 来源备份记录 id（history 模式时填）
    restore_mode        VARCHAR(16)  NOT NULL,                   -- cover | upsert
    tables              JSONB        NOT NULL DEFAULT '[]'::jsonb,
    tables_count        INTEGER      NOT NULL DEFAULT 0,
    pre_backup_id       BIGINT,                                  -- 恢复前自动备份 id（v1 暂不实现，v2 留接口）
    progress            INTEGER      NOT NULL DEFAULT 0,
    progress_msg        VARCHAR(255) NOT NULL DEFAULT '',
    status              VARCHAR(16)  NOT NULL DEFAULT 'pending', -- pending | running | success | failed
    rows_inserted       BIGINT       NOT NULL DEFAULT 0,
    rows_skipped        BIGINT       NOT NULL DEFAULT 0,
    error_message       TEXT,
    started_at          TIMESTAMPTZ,
    finished_at         TIMESTAMPTZ,
    created_by          INTEGER      NOT NULL,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_sys_restore_records_status           ON sys_restore_records (status);
CREATE INDEX IF NOT EXISTS ix_sys_restore_records_created_by       ON sys_restore_records (created_by);
CREATE INDEX IF NOT EXISTS ix_sys_restore_records_created_at       ON sys_restore_records (created_at DESC);
CREATE INDEX IF NOT EXISTS ix_sys_restore_records_source_backup_id ON sys_restore_records (source_backup_id);

COMMENT ON TABLE  sys_restore_records                  IS '恢复任务记录：一次恢复 = 一行';
COMMENT ON COLUMN sys_restore_records.source_type      IS 'file=本地路径 / upload=前端上传 / history=从历史备份选';
COMMENT ON COLUMN sys_restore_records.restore_mode     IS 'cover=全量覆盖（DROP+CREATE+COPY） / upsert=增量（ON CONFLICT DO NOTHING）';
COMMENT ON COLUMN sys_restore_records.pre_backup_id    IS '恢复前自动做的备份 id，v1 暂不实现，保留为 v2 接口';
COMMENT ON COLUMN sys_restore_records.status             IS 'pending=排队 / running=执行中 / success=成功 / failed=失败';