import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

dsn = "postgresql+asyncpg://zhouch:zhouchenhui@8.148.204.54:5432/attribution"

async def main():
    eng = create_async_engine(dsn)
    async with eng.connect() as c:
        # 用 cancel signal 而不是 terminate
        r = await c.execute(text("""
            SELECT pid, state, wait_event, left(query, 80), xact_start
            FROM pg_stat_activity
            WHERE state != 'idle'
              OR (state = 'idle' AND xact_start < now() - interval '1 minute')
            ORDER BY xact_start NULLS LAST
        """))
        print("all blocked:")
        for row in list(r):
            print(f"  pid={row[0]} state={row[1]} wait={row[2]} xact_start={row[4]} q={row[3][:60]}")

        # 尝试 cancel
        for pid in [508068, 508240, 508400, 503847, 508538, 508633, 508951, 509155, 509155]:
            try:
                r = await c.execute(text(f"SELECT pg_cancel_backend({pid})"))
                print(f"  cancel pid={pid}: {list(r)}")
            except Exception as e:
                print(f"  cancel pid={pid}: {e}")

        # 再 terminate
        for pid in [508068, 508240, 508400, 503847, 508538, 508633, 508951, 509155]:
            try:
                r = await c.execute(text(f"SELECT pg_terminate_backend({pid})"))
                print(f"  terminate pid={pid}: {list(r)}")
            except Exception as e:
                print(f"  terminate pid={pid}: {e}")
    await eng.dispose()

asyncio.run(main())
