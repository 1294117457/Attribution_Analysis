import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

dsn = "postgresql+asyncpg://zhouch:zhouchenhui@8.148.204.54:5432/attribution"

async def main():
    eng = create_async_engine(dsn)
    async with eng.connect() as c:
        r = await c.execute(text("SELECT pid, state, query_start, wait_event_type, wait_event, left(query, 80) FROM pg_stat_activity WHERE state != 'idle' ORDER BY query_start LIMIT 20"))
        rows = list(r)
        print(f"  active queries: {len(rows)}")
        for row in rows:
            print(f"    pid={row[0]} state={row[1]} wait={row[4]} query={row[5]}")
        r = await c.execute(text("SELECT pid, state, application_name, query_start, left(query, 80) FROM pg_stat_activity ORDER BY query_start LIMIT 30"))
        print()
        print("All connections:")
        for row in list(r):
            print(f"  pid={row[0]} state={row[1]} app={row[2]} started={row[3]} query={row[4]}")
    await eng.dispose()

asyncio.run(main())
