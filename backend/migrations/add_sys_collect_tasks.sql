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

-- 采集任务明细表
CREATE TABLE IF NOT EXISTS sys_collect_task_details (
    id            SERIAL PRIMARY KEY,
    task_id       INTEGER      NOT NULL,
    symbol        VARCHAR(10)  NOT NULL,
    status        VARCHAR(16)  NOT NULL,
    saved_count   INTEGER      NOT NULL DEFAULT 0,
    error_message TEXT,
    duration_ms   INTEGER,
    created_at    TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_sys_collect_task_details_task
    ON sys_collect_task_details (task_id);
