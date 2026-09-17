"""一次性迁移脚本：修复 tech_kline_dailys 表

问题：create_all 在 rename 之前执行，创建了一张空的 tech_kline_dailys，
导致旧表 daily_klines（有数据）没能 rename 成功。

执行方式：
  cd backend
  python fix_tech_kline_table.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from infrastructure.config import get_settings


async def main():
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=True)

    async with engine.begin() as conn:
        # 1. 检查两张表是否都存在
        result = await conn.execute(text(
            "SELECT tablename FROM pg_tables "
            "WHERE schemaname = 'public' AND tablename IN ('daily_klines', 'tech_kline_dailys')"
        ))
        tables = [r[0] for r in result.fetchall()]
        print(f"\n当前存在的表: {tables}")

        if "daily_klines" in tables and "tech_kline_dailys" in tables:
            # 两张都在：删掉空的新表，然后 rename 旧表
            print("=> 两张表都存在，删除空的 tech_kline_dailys，rename daily_klines")
            await conn.execute(text("DROP TABLE tech_kline_dailys"))
            await conn.execute(text("ALTER TABLE daily_klines RENAME TO tech_kline_dailys"))

        elif "daily_klines" in tables and "tech_kline_dailys" not in tables:
            # 只有旧表：直接 rename
            print("=> 只有 daily_klines，直接 rename")
            await conn.execute(text("ALTER TABLE daily_klines RENAME TO tech_kline_dailys"))

        elif "tech_kline_dailys" in tables and "daily_klines" not in tables:
            # 只有新表：可能已经 rename 过了，或者是空表
            count = await conn.execute(text("SELECT count(*) FROM tech_kline_dailys"))
            row_count = count.scalar()
            print(f"=> 只有 tech_kline_dailys，包含 {row_count} 条数据")
            if row_count == 0:
                print("   警告：tech_kline_dailys 是空表，旧数据可能已丢失！")
            else:
                print("   表已就绪，无需操作。")
            await engine.dispose()
            return

        else:
            print("=> 两张表都不存在，跳过（启动应用时 create_all 会创建）")
            await engine.dispose()
            return

        # 2. rename 索引
        index_renames = [
            ("uq_kline_symbol_date", "uq_tech_kline_symbol_date"),
            ("ix_kline_symbol_date", "ix_tech_kline_symbol_date"),
        ]
        for old_name, new_name in index_renames:
            try:
                await conn.execute(text(f"ALTER INDEX IF EXISTS {old_name} RENAME TO {new_name}"))
                print(f"   索引 {old_name} => {new_name}")
            except Exception as e:
                print(f"   索引 rename 跳过: {old_name} ({e})")

    await engine.dispose()

    # 3. 验证
    engine2 = create_async_engine(settings.DATABASE_URL)
    async with engine2.begin() as conn:
        count = await conn.execute(text("SELECT count(*) FROM tech_kline_dailys"))
        row_count = count.scalar()
        print(f"\n完成！tech_kline_dailys 包含 {row_count} 条数据。")
    await engine2.dispose()


if __name__ == "__main__":
    asyncio.run(main())
