-- =============================================================
-- V4: 基础数据 + 市场 + 概念 + 池
-- =============================================================

-- ── 基础数据 ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS base_adj_factors (
    id           BIGSERIAL PRIMARY KEY,
    symbol       VARCHAR(10) NOT NULL,
    trade_date   DATE NOT NULL,
    adj_factor   DOUBLE PRECISION NOT NULL,
    data_source  VARCHAR(16) NOT NULL DEFAULT 'tushare',
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_base_adj_factors_uk UNIQUE (symbol, trade_date)
);
CREATE INDEX IF NOT EXISTS ix_base_adj_factors_symbol      ON base_adj_factors (symbol);
CREATE INDEX IF NOT EXISTS ix_base_adj_factors_date        ON base_adj_factors (trade_date);
CREATE INDEX IF NOT EXISTS ix_base_adj_factors_symbol_date ON base_adj_factors (symbol, trade_date);

CREATE TABLE IF NOT EXISTS base_dividends (
    id            BIGSERIAL PRIMARY KEY,
    symbol        VARCHAR(10) NOT NULL,
    end_date      DATE NOT NULL,
    ann_date      DATE,
    record_date   DATE,
    ex_date       DATE,
    pay_date      DATE,
    div_proc      VARCHAR(16),
    stk_div       DOUBLE PRECISION,
    stk_bo_rate   DOUBLE PRECISION,
    stk_co_rate   DOUBLE PRECISION,
    cash_div      DOUBLE PRECISION,
    cash_div_tax  DOUBLE PRECISION,
    data_source   VARCHAR(16) NOT NULL DEFAULT 'tushare',
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_base_dividends_uk UNIQUE (symbol, end_date, div_proc)
);
CREATE INDEX IF NOT EXISTS ix_base_dividends_symbol ON base_dividends (symbol);
CREATE INDEX IF NOT EXISTS ix_base_dividends_date   ON base_dividends (end_date);

CREATE TABLE IF NOT EXISTS base_suspends (
    id              BIGSERIAL PRIMARY KEY,
    symbol          VARCHAR(10) NOT NULL,
    trade_date      DATE NOT NULL,
    suspend_timing  DATE,
    suspend_type    VARCHAR(8),
    data_source     VARCHAR(16) NOT NULL DEFAULT 'tushare',
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_base_suspends_symbol      ON base_suspends (symbol);
CREATE INDEX IF NOT EXISTS ix_base_suspends_date        ON base_suspends (trade_date);
CREATE INDEX IF NOT EXISTS ix_base_suspends_symbol_date ON base_suspends (symbol, trade_date);

CREATE TABLE IF NOT EXISTS base_name_changes (
    id              BIGSERIAL PRIMARY KEY,
    symbol          VARCHAR(10) NOT NULL,
    name            VARCHAR(64) NOT NULL,
    start_date      DATE NOT NULL,
    end_date        DATE,
    ann_date        DATE,
    change_reason   VARCHAR(64),
    data_source     VARCHAR(16) NOT NULL DEFAULT 'tushare',
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_base_name_change_uk UNIQUE (symbol, start_date)
);
CREATE INDEX IF NOT EXISTS ix_base_name_changes_symbol ON base_name_changes (symbol);

-- ── 市场 ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS mkt_calendars (
    id              BIGSERIAL PRIMARY KEY,
    exchange        VARCHAR(16) NOT NULL,
    cal_date        DATE NOT NULL,
    is_open         BOOLEAN NOT NULL DEFAULT TRUE,
    pretrade_date   DATE,
    data_source     VARCHAR(16) NOT NULL DEFAULT 'tushare',
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_mkt_calendars_uk UNIQUE (cal_date, exchange)
);
CREATE INDEX IF NOT EXISTS ix_mkt_calendars_exchange      ON mkt_calendars (exchange);
CREATE INDEX IF NOT EXISTS ix_mkt_calendars_exchange_date ON mkt_calendars (exchange, cal_date);

CREATE TABLE IF NOT EXISTS mkt_market_dailys (
    id           BIGSERIAL PRIMARY KEY,
    market       VARCHAR(16) NOT NULL,
    trade_date   DATE NOT NULL,
    close        DOUBLE PRECISION,
    open         DOUBLE PRECISION,
    high         DOUBLE PRECISION,
    low          DOUBLE PRECISION,
    pre_close    DOUBLE PRECISION,
    change       DOUBLE PRECISION,
    pct_chg      DOUBLE PRECISION,
    vol          DOUBLE PRECISION,
    amount       DOUBLE PRECISION,
    data_source  VARCHAR(16) NOT NULL DEFAULT 'tushare',
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_mkt_market_dailys_uk UNIQUE (market, trade_date)
);
CREATE INDEX IF NOT EXISTS ix_mkt_market_dailys_date        ON mkt_market_dailys (trade_date);
CREATE INDEX IF NOT EXISTS ix_mkt_market_dailys_market_date ON mkt_market_dailys (market, trade_date);

CREATE TABLE IF NOT EXISTS mkt_index_members (
    id              BIGSERIAL PRIMARY KEY,
    sector_type     VARCHAR(16) NOT NULL,
    sector_code     VARCHAR(32) NOT NULL,
    sector_name     VARCHAR(64),
    symbol          VARCHAR(10) NOT NULL,
    name            VARCHAR(50),
    effective_date  DATE,
    expiry_date     DATE,
    is_new          VARCHAR(8),
    data_source     VARCHAR(16) NOT NULL DEFAULT 'tushare',
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_mkt_index_members_uk UNIQUE (sector_type, sector_code, symbol, effective_date)
);
CREATE INDEX IF NOT EXISTS ix_mkt_index_members_symbol  ON mkt_index_members (symbol);
CREATE INDEX IF NOT EXISTS ix_mkt_index_members_sector  ON mkt_index_members (sector_type, sector_code);

CREATE TABLE IF NOT EXISTS mkt_sector_dailys (
    id              BIGSERIAL PRIMARY KEY,
    sector_type     VARCHAR(16) NOT NULL,
    sector_code     VARCHAR(32) NOT NULL,
    sector_name     VARCHAR(64),
    trade_date      DATE NOT NULL,
    close           DOUBLE PRECISION,
    open            DOUBLE PRECISION,
    high            DOUBLE PRECISION,
    low             DOUBLE PRECISION,
    pre_close       DOUBLE PRECISION,
    change          DOUBLE PRECISION,
    pct_change      DOUBLE PRECISION,
    vol             DOUBLE PRECISION,
    amount          DOUBLE PRECISION,
    turnover_rate   DOUBLE PRECISION,
    data_source     VARCHAR(16) NOT NULL DEFAULT 'tushare',
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_mkt_sector_dailys_uk UNIQUE (sector_type, sector_code, trade_date)
);
CREATE INDEX IF NOT EXISTS ix_mkt_sector_dailys_type_date ON mkt_sector_dailys (sector_type, trade_date);
CREATE INDEX IF NOT EXISTS ix_mkt_sector_dailys_code      ON mkt_sector_dailys (sector_code);

-- ── 概念 ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS concepts (
    id              BIGSERIAL PRIMARY KEY,
    concept_code    VARCHAR(20)  NOT NULL UNIQUE,
    concept_name    VARCHAR(100) NOT NULL,
    market          VARCHAR(20),
    source          VARCHAR(20),
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_concepts_source ON concepts (source);

CREATE TABLE IF NOT EXISTS concept_members (
    id              BIGSERIAL PRIMARY KEY,
    concept_id      BIGINT NOT NULL,
    concept_code    VARCHAR(20) NOT NULL,
    symbol          VARCHAR(10) NOT NULL,
    name            VARCHAR(50),
    effective_date  DATE,
    expiry_date     DATE,
    is_new          VARCHAR(8),
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_concept_members_concept_id   ON concept_members (concept_id);
CREATE INDEX IF NOT EXISTS ix_concept_members_symbol       ON concept_members (symbol);
CREATE INDEX IF NOT EXISTS ix_concept_members_concept_code ON concept_members (concept_code);

-- ── 池 ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS stock_pools (
    id              BIGSERIAL PRIMARY KEY,
    name            VARCHAR(64) NOT NULL,
    description     VARCHAR(255),
    pool_type       VARCHAR(32) NOT NULL DEFAULT 'custom',
    color           VARCHAR(16),
    icon            VARCHAR(32),
    sort_order      INTEGER NOT NULL DEFAULT 0,
    is_default      BOOLEAN NOT NULL DEFAULT FALSE,
    is_archived     BOOLEAN NOT NULL DEFAULT FALSE,
    owner_id        INTEGER,
    share_token     VARCHAR(64),
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_stock_pools_name        ON stock_pools (name);
CREATE INDEX IF NOT EXISTS ix_stock_pools_pool_type   ON stock_pools (pool_type);
CREATE INDEX IF NOT EXISTS ix_stock_pools_is_default  ON stock_pools (is_default);
CREATE INDEX IF NOT EXISTS ix_stock_pools_updated_at  ON stock_pools (updated_at);

CREATE TABLE IF NOT EXISTS stock_pool_members (
    pool_id     BIGINT NOT NULL,
    symbol      VARCHAR(10) NOT NULL,
    memo        VARCHAR(255),
    sort_order  INTEGER NOT NULL DEFAULT 0,
    added_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (pool_id, symbol)
);
CREATE INDEX IF NOT EXISTS ix_stock_pool_members_pool_id ON stock_pool_members (pool_id);
CREATE INDEX IF NOT EXISTS ix_stock_pool_members_symbol  ON stock_pool_members (symbol);

CREATE TABLE IF NOT EXISTS pool_operations (
    id                BIGSERIAL PRIMARY KEY,
    pool_id           BIGINT,
    operation_type    VARCHAR(32) NOT NULL,
    status            VARCHAR(16) NOT NULL DEFAULT 'pending',
    params            JSONB NOT NULL DEFAULT '{}'::jsonb,
    result_summary    JSONB,
    progress          JSONB NOT NULL DEFAULT '{"done":0,"total":0,"failed":0}'::jsonb,
    error_message     TEXT,
    started_at        TIMESTAMP,
    finished_at       TIMESTAMP,
    created_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_pool_operations_type_status ON pool_operations (operation_type, status);
CREATE INDEX IF NOT EXISTS ix_pool_operations_created_at  ON pool_operations (created_at);
CREATE INDEX IF NOT EXISTS ix_pool_operations_pool_time   ON pool_operations (pool_id, created_at);
