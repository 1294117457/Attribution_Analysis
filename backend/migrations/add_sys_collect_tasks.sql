-- 采集任务日志表
CREATE TABLE IF NOT EXISTS sys_collect_tasks (
    id            SERIAL PRIMARY KEY,
    task_type     VARCHAR(32)  NOT NULL,
    trigger_type  VARCHAR(16)  NOT NULL DEFAULT 'manual',
    params        JSONB,
    status        VARCHAR(16)  NOT NULL DEFAULT 'pending',
    total_count   INTEGER      NOT NULL DEFAULT 0,
    success_count INTEGER      NOT NULL DEFAULT 0,
    fail_count    INTEGER      NOT NULL DEFAULT 0,
    skip_count    INTEGER      NOT NULL DEFAULT 0,
    started_at    TIMESTAMP,
    finished_at   TIMESTAMP,
    duration_ms   INTEGER,
    message       TEXT,
    created_at    TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_sys_collect_tasks_type_time
    ON sys_collect_tasks (task_type, started_at);

-- 注：原 sys_collect_task_details（采集单元明细）表已废弃，不再创建。
--     单元级进度走 Redis + UnitTally 内存聚合，无落地需求。
--     如本地库仍残留该表，可手动 DROP TABLE sys_collect_task_details;
