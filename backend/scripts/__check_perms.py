import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

dsn = "postgresql+asyncpg://zhouch:zhouchenhui@8.148.204.54:5432/attribution"

async def main():
    eng = create_async_engine(dsn)
    async with eng.connect() as c:
        # 看自己是谁
        r = await c.execute(text("SELECT current_user, session_user, current_database()"))
        print("current:", list(r))

        # 看所有 session 的 granted 权限
        r = await c.execute(text("SELECT pid, usename, application_name, client_addr, backend_start FROM pg_stat_activity ORDER BY backend_start"))
        for row in list(r):
            print(f"  pid={row[0]} user={row[1]} app={row[2]} addr={row[3]} started={row[4]}")

        # 看有没有 pg_terminate 的授权
        r = await c.execute(text("""
            SELECT has_parameter_privilege('zhouch', 'log_statement', 'ALTER SYSTEM') as alt_sys
        """))
        print("alt_sys:", list(r))

        r = await c.execute(text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = 'zhouch'"))
        print("zhouch role:", list(r))

        # 看 stock_infos 表锁
        r = await c.execute(text("SELECT locktype, mode, granted, pid FROM pg_locks WHERE relation = 'stock_infos'::regclass"))
        for row in list(r):
            print(f"  stock_infos lock: {row}")

    await eng.dispose()

asyncio.run(main())
