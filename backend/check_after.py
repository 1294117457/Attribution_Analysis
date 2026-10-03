import asyncio
import asyncpg
import redis.asyncio as redis_aio

async def main():
    # Check DB tables
    conn = await asyncpg.connect(
        "postgresql://zhouch:zhouchenhui@8.148.204.54:5432/attribution",
        timeout=10,
    )
    rows = await conn.fetch("""
        SELECT tablename FROM pg_tables
        WHERE schemaname='public'
          AND tablename IN ('sys_email_verifications', 'sys_refresh_tokens', 'sys_captchas')
        ORDER BY tablename
    """)
    print("Legacy tables in DB after backend startup:", [r['tablename'] for r in rows] or "(none — migration 005 applied)")

    # Check Redis captcha
    r = redis_aio.from_url("redis://:zhouchenhui@8.148.204.54:6379/0")
    pong = await r.ping()
    print("Redis ping:", pong)
    captcha_keys = await r.keys("captcha:*")
    print(f"Captcha keys in Redis: {len(captcha_keys)}")
    await conn.close()
    await r.aclose()

asyncio.run(main())
