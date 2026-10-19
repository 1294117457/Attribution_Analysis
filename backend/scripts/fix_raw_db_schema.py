"""raw_data_db 表结构修复与建表脚本

⚠️ 本脚本按 docs/backend-docs/dev/level2/step1采集模块优化/01接口文档-数据库/01-字段对账与修复方案.md 设计

执行内容：
1. 给已存在的 24 张表按 §2/§4 补字段（用 ADD COLUMN IF NOT EXISTS，幂等）
2. 修 §2.1 tech_suspend.suspend_timing 类型（date → varchar）
3. 修 §2.2 concept_snapshot 字段语义（pct_change → p_change，并新增 pct_change/trade_date）
4. 按 §3 新建 5 张表（capital_moneyflow_hsgt / capital_hsgt_top10 / capital_limit_list_d / news_article / fundamental_stock_concept）
5. 修 §4 全部缺字段
6. 跑完后用 check_orm_columns 风格对账

用法：
    cd backend
    python -m scripts.fix_raw_db_schema
"""
import asyncio
import sys
from pathlib import Path

# 关键：把 src/ 加入 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import text
from shared.infrastructure.connection.db_factory import raw_async_engine
from shared.infrastructure.persistence.orm_base import RawBase

# ========== 强制 import 所有 raw ORM（让 RawBase.metadata 加载所有表） ==========
import contexts.market.infrastructure.persistence.models.stock_info  # noqa: F401
import contexts.market.infrastructure.persistence.models.fin_daily_basic  # noqa: F401
import contexts.market.infrastructure.persistence.models.fin_report  # noqa: F401
import contexts.market.infrastructure.persistence.models.fin_top10_holders  # noqa: F401
import contexts.market.infrastructure.persistence.models.fin_top10_float  # noqa: F401
import contexts.market.infrastructure.persistence.models.base_dividend  # noqa: F401
import contexts.market.infrastructure.persistence.models.mkt_index_member  # noqa: F401
import contexts.market.infrastructure.persistence.models.mkt_sector_daily  # noqa: F401
import contexts.market.infrastructure.persistence.models.mkt_market_daily  # noqa: F401
import contexts.market.infrastructure.persistence.models.tech_kline  # noqa: F401
import contexts.market.infrastructure.persistence.models.base_adj_factor  # noqa: F401
import contexts.market.infrastructure.persistence.models.base_name_change  # noqa: F401
import contexts.market.infrastructure.persistence.models.base_suspend  # noqa: F401
import contexts.market.infrastructure.persistence.models.mkt_calendar  # noqa: F401
import contexts.market.infrastructure.persistence.models.cap_moneyflow  # noqa: F401
import contexts.market.infrastructure.persistence.models.cap_margin_detail  # noqa: F401
import contexts.market.infrastructure.persistence.models.cap_margin  # noqa: F401
import contexts.market.infrastructure.persistence.models.cap_top_list  # noqa: F401
import contexts.market.infrastructure.persistence.models.cap_top_inst  # noqa: F401
import contexts.market.infrastructure.persistence.models.cap_block_trade  # noqa: F401
import contexts.market.infrastructure.persistence.models.cap_holder_num  # noqa: F401
import contexts.concept.infrastructure.persistence.models.concept  # noqa: F401
import contexts.collect.infrastructure.persistence.models.cap_moneyflow_hsgt  # noqa: F401
import contexts.collect.infrastructure.persistence.models.cap_hsgt_top10  # noqa: F401
import contexts.collect.infrastructure.persistence.models.capital_limit_list_d  # noqa: F401
import contexts.collect.infrastructure.persistence.models.news_article  # noqa: F401
import contexts.collect.infrastructure.persistence.models.fundamental_stock_concept  # noqa: F401


# ========== §2 P0 严重修复 ==========

P0_FIXES = [
    # §2.1 tech_suspend.suspend_timing: date → varchar(32)
    """
    DO $$
    BEGIN
      IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND table_name='tech_suspend'
          AND column_name='suspend_timing' AND data_type='date'
      ) THEN
        ALTER TABLE public.tech_suspend
          ALTER COLUMN suspend_timing TYPE varchar(32)
            USING (suspend_timing::varchar);
        RAISE NOTICE 'tech_suspend.suspend_timing: date -> varchar(32)';
      ELSE
        RAISE NOTICE 'tech_suspend.suspend_timing: 已是 varchar, 跳过';
      END IF;
    END$$;
    """,

    # §2.2 concept_snapshot: 补 trade_date + 改 pct_change 语义
    # 1) 补 trade_date
    """
    ALTER TABLE public.fundamental_concept_snapshot
      ADD COLUMN IF NOT EXISTS trade_date date;
    """,
    # 2) 原 pct_change 装的是涨跌额（change），重命名为 p_change
    """
    DO $$
    BEGIN
      IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND table_name='fundamental_concept_snapshot'
          AND column_name='pct_change'
      ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND table_name='fundamental_concept_snapshot'
          AND column_name='p_change'
      ) THEN
        ALTER TABLE public.fundamental_concept_snapshot
          RENAME COLUMN pct_change TO p_change;
        RAISE NOTICE 'fundamental_concept_snapshot.pct_change -> p_change';
      ELSE
        RAISE NOTICE 'fundamental_concept_snapshot.pct_change: 已处理, 跳过';
      END IF;
    END$$;
    """,
    # 3) 新加 pct_change（涨跌幅）
    """
    ALTER TABLE public.fundamental_concept_snapshot
      ADD COLUMN IF NOT EXISTS pct_change double precision;
    """,
]


# ========== §4 P2 缺字段修复（全部用 IF NOT EXISTS，幂等） ==========

P2_FIXES = [
    # §4.1 fundamental_stock_info: 补 4 字段
    "ALTER TABLE public.fundamental_stock_info ADD COLUMN IF NOT EXISTS fullname varchar(200);",
    "ALTER TABLE public.fundamental_stock_info ADD COLUMN IF NOT EXISTS enname varchar(200);",
    "ALTER TABLE public.fundamental_stock_info ADD COLUMN IF NOT EXISTS cnspell varchar(20);",
    "ALTER TABLE public.fundamental_stock_info ADD COLUMN IF NOT EXISTS curr_type varchar(8);",

    # §4.2 capital_margin_detail: 补 name
    "ALTER TABLE public.capital_margin_detail ADD COLUMN IF NOT EXISTS name varchar(50);",

    # §4.3 fundamental_daily_basic: 补 limit_status
    "ALTER TABLE public.fundamental_daily_basic ADD COLUMN IF NOT EXISTS limit_status integer;",

    # §4.4 fundamental_top10_float: 补 hold_float_ratio
    "ALTER TABLE public.fundamental_top10_float ADD COLUMN IF NOT EXISTS hold_float_ratio double precision;",

    # §4.5 fundamental_dividend: 补 2 字段
    "ALTER TABLE public.fundamental_dividend ADD COLUMN IF NOT EXISTS div_listdate date;",
    "ALTER TABLE public.fundamental_dividend ADD COLUMN IF NOT EXISTS imp_ann_date date;",

    # §4.6 fundamental_concept_member: 补 short_name
    "ALTER TABLE public.fundamental_concept_member ADD COLUMN IF NOT EXISTS short_name varchar(50);",

    # §4.7 fundamental_report: 补 end_type
    "ALTER TABLE public.fundamental_report ADD COLUMN IF NOT EXISTS end_type varchar(8);",
]


# ========== §3 P1 5 张新表（手写 DDL，幂等） ==========

P1_NEW_TABLES = [
    # capital_moneyflow_hsgt
    """
    CREATE TABLE IF NOT EXISTS public.capital_moneyflow_hsgt (
        id              integer       PRIMARY KEY,
        trade_date      date          NOT NULL,
        symbol          varchar(10)   NOT NULL,
        name            varchar(50),
        market_type     varchar(8)    NOT NULL,
        close           double precision,
        p_change        double precision,
        pct_change      double precision,
        rank            integer,
        amount          double precision,
        net_amount      double precision,
        buy             double precision,
        sell            double precision,
        data_source     varchar(16)   NOT NULL,
        created_at      timestamp     NOT NULL DEFAULT now(),
        updated_at      timestamp     NOT NULL DEFAULT now()
    );
    """,
    "CREATE SEQUENCE IF NOT EXISTS public.capital_moneyflow_hsgt_id_seq AS integer START 1;",
    "ALTER TABLE public.capital_moneyflow_hsgt ALTER COLUMN id SET DEFAULT nextval('capital_moneyflow_hsgt_id_seq'::regclass);",
    """
    DO $$
    BEGIN
      IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='uq_capital_moneyflow_hsgt_uk') THEN
        ALTER TABLE public.capital_moneyflow_hsgt
          ADD CONSTRAINT uq_capital_moneyflow_hsgt_uk UNIQUE (trade_date, symbol, market_type);
      END IF;
    END$$;
    """,
    "CREATE INDEX IF NOT EXISTS ix_capital_moneyflow_hsgt_trade_date ON public.capital_moneyflow_hsgt (trade_date);",
    "CREATE INDEX IF NOT EXISTS ix_capital_moneyflow_hsgt_symbol ON public.capital_moneyflow_hsgt (symbol);",
    "CREATE INDEX IF NOT EXISTS ix_capital_moneyflow_hsgt_symbol_date ON public.capital_moneyflow_hsgt (symbol, trade_date);",

    # capital_hsgt_top10
    """
    CREATE TABLE IF NOT EXISTS public.capital_hsgt_top10 (
        id            integer       PRIMARY KEY,
        trade_date    date          NOT NULL,
        symbol        varchar(10)   NOT NULL,
        name          varchar(50),
        market_type   varchar(8)    NOT NULL,
        rank          integer       NOT NULL,
        close         double precision,
        p_change      double precision,
        amount        double precision,
        net_amount    double precision,
        buy           double precision,
        sell          double precision,
        data_source   varchar(16)   NOT NULL,
        created_at    timestamp     NOT NULL DEFAULT now(),
        updated_at    timestamp     NOT NULL DEFAULT now()
    );
    """,
    "CREATE SEQUENCE IF NOT EXISTS public.capital_hsgt_top10_id_seq AS integer START 1;",
    "ALTER TABLE public.capital_hsgt_top10 ALTER COLUMN id SET DEFAULT nextval('capital_hsgt_top10_id_seq'::regclass);",
    """
    DO $$
    BEGIN
      IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='uq_capital_hsgt_top10_uk') THEN
        ALTER TABLE public.capital_hsgt_top10
          ADD CONSTRAINT uq_capital_hsgt_top10_uk UNIQUE (trade_date, market_type, symbol, rank);
      END IF;
    END$$;
    """,
    "CREATE INDEX IF NOT EXISTS ix_capital_hsgt_top10_trade_date ON public.capital_hsgt_top10 (trade_date);",
    "CREATE INDEX IF NOT EXISTS ix_capital_hsgt_top10_symbol ON public.capital_hsgt_top10 (symbol);",
    "CREATE INDEX IF NOT EXISTS ix_capital_hsgt_top10_market_date ON public.capital_hsgt_top10 (market_type, trade_date);",

    # capital_limit_list_d
    """
    CREATE TABLE IF NOT EXISTS public.capital_limit_list_d (
        id              integer       PRIMARY KEY,
        trade_date      date          NOT NULL,
        symbol          varchar(10)   NOT NULL,
        industry        varchar(64),
        name            varchar(50),
        close           double precision,
        pct_chg         double precision,
        amount          double precision,
        limit_amount    double precision,
        float_mv        double precision,
        total_mv        double precision,
        turnover_ratio  double precision,
        fd_amount       double precision,
        first_time      varchar(8),
        last_time       varchar(8),
        open_times      integer,
        up_stat         varchar(16),
        limit_times     integer,
        limit_type      varchar(8)    NOT NULL,
        data_source     varchar(16)   NOT NULL,
        created_at      timestamp     NOT NULL DEFAULT now(),
        updated_at      timestamp     NOT NULL DEFAULT now()
    );
    """,
    "CREATE SEQUENCE IF NOT EXISTS public.capital_limit_list_d_id_seq AS integer START 1;",
    "ALTER TABLE public.capital_limit_list_d ALTER COLUMN id SET DEFAULT nextval('capital_limit_list_d_id_seq'::regclass);",
    """
    DO $$
    BEGIN
      IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='uq_capital_limit_list_d_uk') THEN
        ALTER TABLE public.capital_limit_list_d
          ADD CONSTRAINT uq_capital_limit_list_d_uk UNIQUE (trade_date, symbol, limit_type);
      END IF;
    END$$;
    """,
    "CREATE INDEX IF NOT EXISTS ix_capital_limit_list_d_trade_date ON public.capital_limit_list_d (trade_date);",
    "CREATE INDEX IF NOT EXISTS ix_capital_limit_list_d_symbol ON public.capital_limit_list_d (symbol);",
    "CREATE INDEX IF NOT EXISTS ix_capital_limit_list_d_symbol_date ON public.capital_limit_list_d (symbol, trade_date);",
    "CREATE INDEX IF NOT EXISTS ix_capital_limit_list_d_type_date ON public.capital_limit_list_d (limit_type, trade_date);",

    # news_article
    """
    CREATE TABLE IF NOT EXISTS public.news_article (
        id              bigint        PRIMARY KEY,
        published_at    timestamp     NOT NULL,
        source          varchar(32),
        channels        text,
        title           varchar(512)  NOT NULL,
        content         text,
        url             varchar(1024),
        symbols         varchar(10)[],
        sentiment       varchar(16),
        category        varchar(32),
        data_source     varchar(16)   NOT NULL,
        created_at      timestamp     NOT NULL DEFAULT now(),
        updated_at      timestamp     NOT NULL DEFAULT now()
    );
    """,
    "CREATE SEQUENCE IF NOT EXISTS public.news_article_id_seq AS bigint START 1;",
    "ALTER TABLE public.news_article ALTER COLUMN id SET DEFAULT nextval('news_article_id_seq'::regclass);",
    """
    DO $$
    BEGIN
      IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='uq_news_article_source_url') THEN
        ALTER TABLE public.news_article
          ADD CONSTRAINT uq_news_article_source_url UNIQUE (source, url);
      END IF;
    END$$;
    """,
    "CREATE INDEX IF NOT EXISTS ix_news_article_published_at ON public.news_article (published_at);",
    "CREATE INDEX IF NOT EXISTS ix_news_article_source ON public.news_article (source);",
    "CREATE INDEX IF NOT EXISTS ix_news_article_symbols ON public.news_article USING gin (symbols);",

    # fundamental_stock_concept
    """
    CREATE TABLE IF NOT EXISTS public.fundamental_stock_concept (
        id              integer       PRIMARY KEY,
        symbol          varchar(10)   NOT NULL,
        concept_id      integer       NOT NULL,
        name            varchar(100),
        source          varchar(10)   DEFAULT 'ths'::varchar NOT NULL,
        reason          text,
        synced_at       timestamp     NOT NULL DEFAULT now(),
        created_at      timestamp     NOT NULL DEFAULT now(),
        updated_at      timestamp     NOT NULL DEFAULT now()
    );
    """,
    "CREATE SEQUENCE IF NOT EXISTS public.fundamental_stock_concept_id_seq AS integer START 1;",
    "ALTER TABLE public.fundamental_stock_concept ALTER COLUMN id SET DEFAULT nextval('fundamental_stock_concept_id_seq'::regclass);",
    """
    DO $$
    BEGIN
      IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='uq_fundamental_stock_concept_uk') THEN
        ALTER TABLE public.fundamental_stock_concept
          ADD CONSTRAINT uq_fundamental_stock_concept_uk UNIQUE (symbol, concept_id);
      END IF;
    END$$;
    """,
    "CREATE INDEX IF NOT EXISTS ix_fundamental_stock_concept_symbol ON public.fundamental_stock_concept (symbol);",
    "CREATE INDEX IF NOT EXISTS ix_fundamental_stock_concept_concept_id ON public.fundamental_stock_concept (concept_id);",
]


# ========== 同步 RawBase.metadata 与 DB（重命名/类型变更后 ORM 状态对齐） ==========
# 关键：上面的 DDL 已修了列名和类型，但 RawBase.metadata 是在 import 时加载的，
# 仍然记录着旧 schema。这里我们用 SQLAlchemy 的 reflect 让 metadata 跟 DB 同步。
async def reflect_metadata(engine):
    async with engine.begin() as conn:
        await conn.run_sync(RawBase.metadata.reflect)


# ========== 主流程 ==========
async def main():
    print("=" * 60)
    print("raw_data_db 表结构修复脚本")
    print("=" * 60)

    async with raw_async_engine.begin() as conn:
        # ===== Step 1: §2 P0 =====
        print("\n[Step 1] §2 P0 严重修复")
        for i, sql in enumerate(P0_FIXES, 1):
            print(f"  [{i}/{len(P0_FIXES)}] 执行 P0 DDL")
            await conn.execute(text(sql))

        # ===== Step 2: §4 P2 补字段 =====
        print("\n[Step 2] §4 P2 缺字段")
        for i, sql in enumerate(P2_FIXES, 1):
            print(f"  [{i}/{len(P2_FIXES)}] {sql[:80]}")
            await conn.execute(text(sql))

    # ===== Step 3: 让 metadata 重新 reflect 一次（让旧表的"已存在列"对齐）=====
    print("\n[Step 3] 重新 reflect metadata（让 SQLAlchemy 知道旧表的新结构）")
    await reflect_metadata(raw_async_engine)

    # ===== Step 4: 5 张新表（直接 raw SQL，不用 create_all 避免索引冲突） =====
    print("\n[Step 4] §3 新建 5 张表（raw SQL）")
    async with raw_async_engine.begin() as conn:
        for i, sql in enumerate(P1_NEW_TABLES, 1):
            print(f"  [{i}/{len(P1_NEW_TABLES)}] {sql[:60]}...")
            await conn.execute(text(sql))

    # ===== Step 5: 对账 =====
    print("\n[Step 5] ORM 期望 vs DB 实际 对账")
    async with raw_async_engine.begin() as conn:
        for table in sorted(RawBase.metadata.sorted_tables, key=lambda t: t.name):
            r = await conn.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_schema='public' AND table_name = :tn
                ORDER BY ordinal_position
            """), {"tn": table.name})
            actual_cols = [row[0] for row in r]
            expected_cols = [c.name for c in table.columns]
            missing = [c for c in expected_cols if c not in actual_cols]
            extra = [c for c in actual_cols if c not in expected_cols]
            if missing or extra:
                print(f"  [ERR] {table.name}")
                if missing: print(f"         ORM 期望但库里缺: {missing}")
                if extra: print(f"         库里有但 ORM 不知道: {extra}")
            else:
                print(f"  [OK ] {table.name}  ({len(expected_cols)} cols)")

    print("\n" + "=" * 60)
    print("✅ 全部完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
