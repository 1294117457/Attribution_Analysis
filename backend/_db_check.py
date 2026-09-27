"""列出所有 concept 表"""
import asyncio
from src.infrastructure.database.connection import async_engine
from sqlalchemy import text


async def go():
    async with async_engine.begin() as conn:
        r = await conn.execute(text("SELECT COUNT(*) FROM stock_concept_members"))
        print('members rows:', r.scalar_one())
        r = await conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE tablename LIKE 'concept%' "
            "OR tablename = 'stock_concept_members' "
            "OR tablename = 'concepts'"
        ))
        print('--- tables ---')
        for row in r:
            print('  ', row[0])


asyncio.run(go())
