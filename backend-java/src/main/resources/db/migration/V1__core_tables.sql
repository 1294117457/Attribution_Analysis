-- =============================================================
-- V1: 核心表 — stock_infos, tech_kline_dailys, sys_collect_tasks
-- =============================================================

CREATE TABLE stock_infos (
    id              BIGSERIAL PRIMARY KEY,
    symbol          VARCHAR(10)  NOT NULL UNIQUE,
    ts_code         VARCHAR(20),
    name            VARCHAR(100),
    area            VARCHAR(50),
    industry        VARCHAR(100),
    market          VARCHAR(50),
    exchange        VARCHAR(10),
    list_date       DATE,
    delist_date     DATE,
    list_status     VARCHAR(5) DEFAULT 'L',
    is_hs           VARCHAR(5) DEFAULT 'N',
    total_shares    BIGINT,
    act_name        VARCHAR(200),
    act_ent_type    VARCHAR(50),
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_stock_industry_market   ON stock_infos (industry, market);
CREATE INDEX ix_stock_exchange_status   ON stock_infos (exchange, list_status);
CREATE INDEX ix_stock_infos_symbol      ON stock_infos (symbol);
CREATE INDEX ix_stock_infos_ts_code     ON stock_infos (ts_code);
CREATE INDEX ix_stock_infos_name        ON stock_infos (name);
CREATE INDEX ix_stock_infos_area        ON stock_infos (area);
CREATE INDEX ix_stock_infos_industry    ON stock_infos (industry);
CREATE INDEX ix_stock_infos_market      ON stock_infos (market);
CREATE INDEX ix_stock_infos_exchange    ON stock_infos (exchange);
CREATE INDEX ix_stock_infos_list_status ON stock_infos (list_status);

CREATE TABLE tech_kline_dailys (
    id              BIGSERIAL PRIMARY KEY,
    symbol          VARCHAR(10)  NOT NULL,
    name            VARCHAR(50),
    date            DATE         NOT NULL,
    open            DOUBLE PRECISION NOT NULL,
    high            DOUBLE PRECISION NOT NULL,
    low             DOUBLE PRECISION NOT NULL,
    close           DOUBLE PRECISION NOT NULL,
    volume          BIGINT       NOT NULL,
    amount          DOUBLE PRECISION NOT NULL,
    change          DOUBLE PRECISION,
    change_pct      DOUBLE PRECISION,
    pre_close       DOUBLE PRECISION,
    ma5             DOUBLE PRECISION,
    ma10            DOUBLE PRECISION,
    ma20            DOUBLE PRECISION,
    ma60            DOUBLE PRECISION,
    ema12           DOUBLE PRECISION,
    ema26           DOUBLE PRECISION,
    macd_dif        DOUBLE PRECISION,
    macd_dea        DOUBLE PRECISION,
    macd_bar        DOUBLE PRECISION,
    rsi6            DOUBLE PRECISION,
    rsi12           DOUBLE PRECISION,
    rsi24           DOUBLE PRECISION,
    kdj_k           DOUBLE PRECISION,
    kdj_d           DOUBLE PRECISION,
    kdj_j           DOUBLE PRECISION,
    boll_mid        DOUBLE PRECISION,
    boll_up         DOUBLE PRECISION,
    boll_dn         DOUBLE PRECISION,
    turnover_rate   DOUBLE PRECISION,
    extra           JSONB,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_tech_kline_symbol_date UNIQUE (symbol, date)
);
CREATE INDEX ix_tech_kline_symbol_date ON tech_kline_dailys (symbol, date);

CREATE TABLE sys_collect_tasks (
    id              BIGSERIAL PRIMARY KEY,
    task_type       VARCHAR(32) NOT NULL,
    trigger_type    VARCHAR(16) NOT NULL DEFAULT 'manual',
    params          JSONB,
    status          VARCHAR(16) NOT NULL DEFAULT 'pending',
    total_count     INTEGER NOT NULL DEFAULT 0,
    success_count   INTEGER NOT NULL DEFAULT 0,
    fail_count      INTEGER NOT NULL DEFAULT 0,
    skip_count      INTEGER NOT NULL DEFAULT 0,
    started_at      TIMESTAMP,
    finished_at     TIMESTAMP,
    duration_ms     INTEGER,
    message         TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_sys_collect_tasks_type_time ON sys_collect_tasks (task_type, started_at);

CREATE TABLE sys_collect_task_details (
    id              BIGSERIAL PRIMARY KEY,
    task_id         BIGINT NOT NULL,
    symbol          VARCHAR(10) NOT NULL,
    status          VARCHAR(16) NOT NULL,
    saved_count     INTEGER NOT NULL DEFAULT 0,
    error_message   TEXT,
    duration_ms     INTEGER,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_sys_collect_task_details_task_id ON sys_collect_task_details (task_id);
