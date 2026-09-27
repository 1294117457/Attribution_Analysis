"""显式创建两张新表"""
import asyncio
from sqlalchemy import text
from src.infrastructure.database.connection import async_engine


async def go():
    # 显式 DDL，避免 ORM 模型未生效
    stmts = [
        """
        CREATE TABLE IF NOT EXISTS concept_snapshots (
            id              SERIAL PRIMARY KEY,
            concept_name    VARCHAR(100) NOT NULL,
            open_price      FLOAT,
            prev_close      FLOAT,
            low             FLOAT,
            high            FLOAT,
            volume_wan      FLOAT,
            pct_change      FLOAT NOT NULL DEFAULT 0.0,
            rank_current    INTEGER,
            rank_total      INTEGER,
            up_count        INTEGER,
            down_count      INTEGER,
            net_inflow_yi   FLOAT,
            turnover_yi     FLOAT,
            source          VARCHAR(10) NOT NULL DEFAULT 'ths',
            captured_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_concept_snapshots_name_captured ON concept_snapshots (concept_name, captured_at)",
        """
        CREATE TABLE IF NOT EXISTS concept_index_ths (
            id              SERIAL PRIMARY KEY,
            concept_name    VARCHAR(100) NOT NULL,
            trade_date      DATE NOT NULL,
            open            FLOAT NOT NULL DEFAULT 0.0,
            high            FLOAT NOT NULL DEFAULT 0.0,
            low             FLOAT NOT NULL DEFAULT 0.0,
            close           FLOAT NOT NULL DEFAULT 0.0,
            volume          INTEGER NOT NULL DEFAULT 0,
            amount          FLOAT NOT NULL DEFAULT 0.0,
            captured_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_concept_index_th_name_date UNIQUE (concept_name, trade_date)
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_concept_index_th_name ON concept_index_ths (concept_name)",
        "CREATE INDEX IF NOT EXISTS ix_concept_index_th_date ON concept_index_ths (trade_date)",
    ]
    async with async_engine.begin() as conn:
        for s in stmts:
            try:
                await conn.execute(text(s))
                print("OK:", s[:50].replace("\n", " "))
            except Exception as e:
                print("FAIL:", s[:50], "->", e)

    async with async_engine.begin() as conn:
        r = await conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE tablename LIKE 'concept%' "
            "OR tablename LIKE '%concept%' ORDER BY tablename"
        ))
        for row in r:
            print('  table:', row[0])


asyncio.run(go())
