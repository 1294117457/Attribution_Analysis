-- =============================================================
-- V3: 资金流向表
-- =============================================================

CREATE TABLE IF NOT EXISTS cap_moneyflows (
    id                BIGSERIAL PRIMARY KEY,
    symbol            VARCHAR(10) NOT NULL,
    trade_date        DATE NOT NULL,
    buy_sm_vol        DOUBLE PRECISION,
    buy_sm_amount     DOUBLE PRECISION,
    sell_sm_vol       DOUBLE PRECISION,
    sell_sm_amount    DOUBLE PRECISION,
    buy_md_vol        DOUBLE PRECISION,
    buy_md_amount     DOUBLE PRECISION,
    sell_md_vol       DOUBLE PRECISION,
    sell_md_amount    DOUBLE PRECISION,
    buy_lg_vol        DOUBLE PRECISION,
    buy_lg_amount     DOUBLE PRECISION,
    sell_lg_vol       DOUBLE PRECISION,
    sell_lg_amount    DOUBLE PRECISION,
    buy_elg_vol       DOUBLE PRECISION,
    buy_elg_amount    DOUBLE PRECISION,
    sell_elg_vol      DOUBLE PRECISION,
    sell_elg_amount   DOUBLE PRECISION,
    net_mf_vol        DOUBLE PRECISION,
    net_mf_amount     DOUBLE PRECISION,
    data_source       VARCHAR(16) NOT NULL DEFAULT 'tushare',
    created_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_cap_moneyflow_symbol_date UNIQUE (symbol, trade_date)
);
CREATE INDEX IF NOT EXISTS ix_cap_moneyflow_symbol      ON cap_moneyflows (symbol);
CREATE INDEX IF NOT EXISTS ix_cap_moneyflow_date        ON cap_moneyflows (trade_date);
CREATE INDEX IF NOT EXISTS ix_cap_moneyflow_symbol_date ON cap_moneyflows (symbol, trade_date);

CREATE TABLE IF NOT EXISTS cap_margins (
    id           BIGSERIAL PRIMARY KEY,
    trade_date   DATE NOT NULL,
    exchange_id  VARCHAR(16) NOT NULL,
    rzye         DOUBLE PRECISION,
    rzmre        DOUBLE PRECISION,
    rzche        DOUBLE PRECISION,
    rqye         DOUBLE PRECISION,
    rqmcl        DOUBLE PRECISION,
    rzrqye       DOUBLE PRECISION,
    rqyl         DOUBLE PRECISION,
    data_source  VARCHAR(16) NOT NULL DEFAULT 'tushare',
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_cap_margins_uk UNIQUE (exchange_id, trade_date)
);
CREATE INDEX IF NOT EXISTS ix_cap_margins_date ON cap_margins (trade_date);

CREATE TABLE IF NOT EXISTS cap_margin_details (
    id           BIGSERIAL PRIMARY KEY,
    symbol       VARCHAR(10) NOT NULL,
    trade_date   DATE NOT NULL,
    rzye         DOUBLE PRECISION,
    rqye         DOUBLE PRECISION,
    rzmre        DOUBLE PRECISION,
    rqyl         DOUBLE PRECISION,
    rzche        DOUBLE PRECISION,
    rqchl        DOUBLE PRECISION,
    rqmcl        DOUBLE PRECISION,
    rzrqye       DOUBLE PRECISION,
    data_source  VARCHAR(16) NOT NULL DEFAULT 'tushare',
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_cap_margin_details_uk UNIQUE (symbol, trade_date)
);
CREATE INDEX IF NOT EXISTS ix_cap_margin_details_symbol      ON cap_margin_details (symbol);
CREATE INDEX IF NOT EXISTS ix_cap_margin_details_date        ON cap_margin_details (trade_date);
CREATE INDEX IF NOT EXISTS ix_cap_margin_details_symbol_date ON cap_margin_details (symbol, trade_date);

CREATE TABLE IF NOT EXISTS cap_top_lists (
    id              BIGSERIAL PRIMARY KEY,
    trade_date      DATE NOT NULL,
    symbol          VARCHAR(10) NOT NULL,
    name            VARCHAR(50),
    close           DOUBLE PRECISION,
    pct_change      DOUBLE PRECISION,
    turnover_rate   DOUBLE PRECISION,
    amount          DOUBLE PRECISION,
    l_sell          DOUBLE PRECISION,
    l_buy           DOUBLE PRECISION,
    l_amount        DOUBLE PRECISION,
    net_amount      DOUBLE PRECISION,
    net_rate        DOUBLE PRECISION,
    amount_rate     DOUBLE PRECISION,
    float_values    DOUBLE PRECISION,
    reason          VARCHAR(256),
    data_source     VARCHAR(16) NOT NULL DEFAULT 'tushare',
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_cap_top_lists_uk UNIQUE (trade_date, symbol, reason)
);
CREATE INDEX IF NOT EXISTS ix_cap_top_lists_symbol      ON cap_top_lists (symbol);
CREATE INDEX IF NOT EXISTS ix_cap_top_lists_date        ON cap_top_lists (trade_date);
CREATE INDEX IF NOT EXISTS ix_cap_top_lists_symbol_date ON cap_top_lists (symbol, trade_date);

CREATE TABLE IF NOT EXISTS cap_top_insts (
    id           BIGSERIAL PRIMARY KEY,
    trade_date   DATE NOT NULL,
    symbol       VARCHAR(10) NOT NULL,
    exalter      VARCHAR(128),
    side         VARCHAR(8),
    buy          DOUBLE PRECISION,
    buy_rate     DOUBLE PRECISION,
    sell         DOUBLE PRECISION,
    sell_rate    DOUBLE PRECISION,
    net_buy      DOUBLE PRECISION,
    reason       VARCHAR(256),
    data_source  VARCHAR(16) NOT NULL DEFAULT 'tushare',
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_cap_top_insts_symbol      ON cap_top_insts (symbol);
CREATE INDEX IF NOT EXISTS ix_cap_top_insts_date        ON cap_top_insts (trade_date);
CREATE INDEX IF NOT EXISTS ix_cap_top_insts_symbol_date ON cap_top_insts (symbol, trade_date);

CREATE TABLE IF NOT EXISTS cap_block_trades (
    id           BIGSERIAL PRIMARY KEY,
    trade_date   DATE NOT NULL,
    symbol       VARCHAR(10) NOT NULL,
    name         VARCHAR(50),
    price        DOUBLE PRECISION,
    vol          DOUBLE PRECISION,
    amount       DOUBLE PRECISION,
    buyer        VARCHAR(128),
    seller       VARCHAR(128),
    data_source  VARCHAR(16) NOT NULL DEFAULT 'tushare',
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_cap_block_trades_symbol      ON cap_block_trades (symbol);
CREATE INDEX IF NOT EXISTS ix_cap_block_trades_date        ON cap_block_trades (trade_date);
CREATE INDEX IF NOT EXISTS ix_cap_block_trades_symbol_date ON cap_block_trades (symbol, trade_date);

CREATE TABLE IF NOT EXISTS cap_holder_nums (
    id           BIGSERIAL PRIMARY KEY,
    symbol       VARCHAR(10) NOT NULL,
    ann_date     DATE,
    end_date     DATE NOT NULL,
    holder_num   INTEGER,
    holder_nums  DOUBLE PRECISION,
    data_source  VARCHAR(16) NOT NULL DEFAULT 'tushare',
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_cap_holder_nums_uk UNIQUE (symbol, end_date)
);
CREATE INDEX IF NOT EXISTS ix_cap_holder_nums_symbol ON cap_holder_nums (symbol);
CREATE INDEX IF NOT EXISTS ix_cap_holder_nums_date   ON cap_holder_nums (end_date);
