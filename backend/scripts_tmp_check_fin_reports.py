"""临时探针：检查 fin_reports 表实际数据状态"""
import asyncio
from sqlalchemy import text, func, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# 后端默认 DSN（生产环境 .env 缺失时的退化默认值）
DSN = "postgresql+asyncpg://postgres:password@localhost:5432/stock_db"

async def main():
    eng = create_async_engine(DSN, echo=False)
    async with eng.connect() as conn:
        # 1. fin_reports 总行数
        r = await conn.execute(text("SELECT COUNT(*) FROM fin_reports"))
        total = r.scalar()
        print(f"[1] fin_reports 总行数: {total}")

        # 2. 有数据的 distinct symbol 数
        r = await conn.execute(text("SELECT COUNT(DISTINCT symbol) FROM fin_reports"))
        syms = r.scalar()
        print(f"[2] 有 fin_reports 的 symbol 数: {syms}")

        # 3. 000001.SZ 的最新利润表记录
        r = await conn.execute(text("""
            SELECT end_date, report_type, revenue, n_income
            FROM fin_reports
            WHERE symbol = '000001.SZ' OR symbol = '000001'
            ORDER BY end_date DESC
            LIMIT 5
        """))
        rows = list(r)
        print(f"[3] 000001 fin_reports (top 5):")
        for row in rows:
            print(f"    {row}")

        # 4. report_type 分布
        r = await conn.execute(text("""
            SELECT report_type, COUNT(*) cnt
            FROM fin_reports
            GROUP BY report_type
        """))
        print(f"[4] report_type 分布:")
        for row in r:
            print(f"    {row}")

        # 5. revenue=0 或 NULL 的比例
        r = await conn.execute(text("""
            SELECT
                SUM(CASE WHEN revenue IS NULL THEN 1 ELSE 0 END) null_rev,
                SUM(CASE WHEN revenue = 0 THEN 1 ELSE 0 END) zero_rev,
                SUM(CASE WHEN n_income IS NULL THEN 1 ELSE 0 END) null_ni,
                COUNT(*) total
            FROM fin_reports
        """))
        print(f"[5] 数据完整性:")
        for row in r:
            print(f"    {row}")

    await eng.dispose()

asyncio.run(main())
