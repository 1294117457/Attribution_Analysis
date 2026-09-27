import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

dsn = "postgresql+asyncpg://zhouch:zhouchenhui@8.148.204.54:5432/attribution"

async def main():
    eng = create_async_engine(dsn)
    async with eng.connect() as c:
        r = await c.execute(text("""
            SELECT pid, state, wait_event, left(query, 80)
            FROM pg_stat_activity
            WHERE state != 'idle' OR xact_start IS NOT NULL
            ORDER BY xact_start NULLS LAST
        """))
        rows = list(r)
        print(f"non-idle: {len(rows)}")
        for row in rows[:20]:
            print(f"  pid={row[0]} state={row[1]} wait={row[2]} q={row[3][:60]}")
    await eng.dispose()

asyncio.run(main())
