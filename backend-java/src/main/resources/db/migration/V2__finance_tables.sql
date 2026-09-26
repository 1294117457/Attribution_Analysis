-- =============================================================
-- V2: 财务表 — fin_reports, fin_daily_basics, fin_top10_holders, fin_top10_floatholders
-- 注意：远端 PostgreSQL 上这些表已存在（来自 Python 工程），本迁移由 IF NOT EXISTS 保护
-- =============================================================

CREATE TABLE IF NOT EXISTS fin_reports (
    id                       BIGSERIAL PRIMARY KEY,
    symbol                   VARCHAR(10)  NOT NULL,
    ann_date                 DATE,
    end_date                 DATE         NOT NULL,
    report_type              VARCHAR(16),
    comp_type                VARCHAR(16),
    basic_eps                DOUBLE PRECISION,
    diluted_eps              DOUBLE PRECISION,
    total_revenue            DOUBLE PRECISION,
    revenue                  DOUBLE PRECISION,
    operate_profit           DOUBLE PRECISION,
    total_profit             DOUBLE PRECISION,
    n_income                 DOUBLE PRECISION,
    n_income_attr_p          DOUBLE PRECISION,
    total_assets             DOUBLE PRECISION,
    total_liab               DOUBLE PRECISION,
    total_hldr_eqy_exc_min_int DOUBLE PRECISION,
    n_cashflow_act           DOUBLE PRECISION,
    n_cash_flows_fnc_act     DOUBLE PRECISION,
    n_cashflow_inv_act       DOUBLE PRECISION,
    data_source              VARCHAR(16) NOT NULL DEFAULT 'tushare',
    created_at               TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at               TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_fin_reports_uk UNIQUE (symbol, end_date, report_type)
);
CREATE INDEX IF NOT EXISTS ix_fin_reports_symbol_end ON fin_reports (symbol, end_date);

CREATE TABLE IF NOT EXISTS fin_daily_basics (
    id              BIGSERIAL PRIMARY KEY,
    symbol          VARCHAR(10)  NOT NULL,
    trade_date      DATE         NOT NULL,
    close           DOUBLE PRECISION,
    turnover_rate   DOUBLE PRECISION,
    turnover_rate_f DOUBLE PRECISION,
    volume_ratio    DOUBLE PRECISION,
    pe              DOUBLE PRECISION,
    pe_ttm          DOUBLE PRECISION,
    pb              DOUBLE PRECISION,
    ps              DOUBLE PRECISION,
    ps_ttm          DOUBLE PRECISION,
    dv_ratio        DOUBLE PRECISION,
    dv_ttm          DOUBLE PRECISION,
    total_share     DOUBLE PRECISION,
    float_share     DOUBLE PRECISION,
    free_share      DOUBLE PRECISION,
    total_mv        DOUBLE PRECISION,
    circ_mv         DOUBLE PRECISION,
    data_source     VARCHAR(16) NOT NULL DEFAULT 'tushare',
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_fin_daily_basics_uk UNIQUE (symbol, trade_date)
);
CREATE INDEX IF NOT EXISTS ix_fin_daily_basics_symbol      ON fin_daily_basics (symbol);
CREATE INDEX IF NOT EXISTS ix_fin_daily_basics_date        ON fin_daily_basics (trade_date);
CREATE INDEX IF NOT EXISTS ix_fin_daily_basics_symbol_date ON fin_daily_basics (symbol, trade_date);

CREATE TABLE IF NOT EXISTS fin_top10_holders (
    id                 BIGSERIAL PRIMARY KEY,
    symbol             VARCHAR(10)  NOT NULL,
    ann_date           DATE,
    end_date           DATE,
    holder_name        VARCHAR(128) NOT NULL,
    hold_amount        DOUBLE PRECISION,
    hold_ratio         DOUBLE PRECISION,
    hold_float_ratio   DOUBLE PRECISION,
    hold_change        DOUBLE PRECISION,
    holder_type        VARCHAR(32),
    data_source        VARCHAR(16) NOT NULL DEFAULT 'tushare',
    created_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_fin_top10_holders_uk UNIQUE (symbol, end_date, ann_date, holder_name)
);
CREATE INDEX IF NOT EXISTS ix_fin_top10_holders_symbol ON fin_top10_holders (symbol);
CREATE INDEX IF NOT EXISTS ix_fin_top10_holders_date   ON fin_top10_holders (end_date);

CREATE TABLE IF NOT EXISTS fin_top10_floatholders (
    id                 BIGSERIAL PRIMARY KEY,
    symbol             VARCHAR(10)  NOT NULL,
    ann_date           DATE,
    end_date           DATE,
    holder_name        VARCHAR(128) NOT NULL,
    hold_amount        DOUBLE PRECISION,
    hold_ratio         DOUBLE PRECISION,
    hold_change        DOUBLE PRECISION,
    holder_type        VARCHAR(32),
    data_source        VARCHAR(16) NOT NULL DEFAULT 'tushare',
    created_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_fin_top10_floatholders_uk UNIQUE (symbol, end_date, ann_date, holder_name)
);
CREATE INDEX IF NOT EXISTS ix_fin_top10_floatholders_symbol ON fin_top10_floatholders (symbol);
CREATE INDEX IF NOT EXISTS ix_fin_top10_floatholders_date   ON fin_top10_floatholders (end_date);
