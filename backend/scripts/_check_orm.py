import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import select
import sys
sys.path.insert(0, r'D:\codes\Attribution_Analysis\backend')
from src.infrastructure.database.models.concept import ConceptsDB, ConceptMemberDB

dsn = "postgresql+asyncpg://zhouch:zhouchenhui@8.148.204.54:5432/attribution"

async def main():
    eng = create_async_engine(dsn)
    async with AsyncSession(eng) as s:
        symbols = ["000001", "000002", "000006"]
        stmt = (
            select(
                ConceptMemberDB.symbol,
                ConceptsDB.id,
                ConceptsDB.name,
                ConceptsDB.source,
                ConceptsDB.concept_type,
            )
            .join(ConceptsDB, ConceptMemberDB.concept_id == ConceptsDB.id)
            .where(
                ConceptMemberDB.symbol.in_(symbols)
            )
        )
        r = await s.execute(stmt)
        rows = r.all()
        print(f"  rows returned: {len(rows)}")
        for r in rows:
            print(f"    {r.symbol} -> {r.name} (id={r.id}, type={r.concept_type}, active={r.is_active if hasattr(r, 'is_active') else 'n/a'})")

    await eng.dispose()

asyncio.run(main())
