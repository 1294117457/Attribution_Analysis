import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

dsn = "postgresql+asyncpg://zhouch:zhouchenhui@8.148.204.54:5432/attribution"

async def main():
    eng = create_async_engine(dsn)
    async with eng.connect() as c:
        r = await c.execute(text("SELECT COUNT(*) FROM stock_concept_members"))
        print("members total:", list(r))
        r = await c.execute(text("SELECT symbol, COUNT(*) FROM stock_concept_members GROUP BY symbol ORDER BY symbol LIMIT 10"))
        print("by symbol top 10:", list(r))
        r = await c.execute(text("SELECT cm.symbol, c.name FROM stock_concept_members cm JOIN concepts c ON c.id = cm.concept_id WHERE cm.symbol IN ('000001', '000002', '000006')"))
        print("000001/000002/000006 members:", list(r))
    await eng.dispose()

asyncio.run(main())
