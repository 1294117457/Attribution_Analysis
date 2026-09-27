import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

dsn = "postgresql+asyncpg://zhouch:zhouchenhui@8.148.204.54:5432/attribution"

async def main():
    eng = create_async_engine(dsn)
    async with eng.connect() as c:
        # 杀掉所有 ALTER TABLE / SELECT concepts 的卡死连接
        r = await c.execute(text("""
            SELECT pg_terminate_backend(pid), pid, state, left(query, 80)
            FROM pg_stat_activity
            WHERE state IN ('idle in transaction', 'active')
              AND (
                query LIKE 'ALTER TABLE stock_infos%'
                OR query LIKE 'ALTER TABLE concepts%'
                OR query LIKE 'SELECT concepts.name%'
                OR query LIKE '%concept%'
              )
              AND pid != pg_backend_pid()
        """))
        rows = list(r)
        print(f"  terminated: {len(rows)}")
        for row in rows[:10]:
            print(f"    {row[1]} {row[2]} {row[3][:60]}")

        # 再次扫描确认
        r = await c.execute(text("""
            SELECT pid, state, left(query, 80)
            FROM pg_stat_activity
            WHERE state IN ('idle in transaction', 'active')
              AND query NOT LIKE '%pg_stat_activity%'
        """))
        print("  remaining:")
        for row in list(r):
            print(f"    {row[0]} {row[1]} {row[2][:60]}")
    await eng.dispose()

asyncio.run(main())
