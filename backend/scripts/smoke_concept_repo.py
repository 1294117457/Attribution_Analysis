"""concept 仓储读方法实库冒烟：临时写入数据 → 验证 JOIN 结果 → 回滚

不落盘：整个过程在一个事务里，最后无条件 rollback。
目的是真正走通 join 逻辑（而不是空表返回空集蒙混过关）。
"""

from __future__ import annotations

import asyncio
import sys
from datetime import date, datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND / "src"))

from sqlalchemy import select  # noqa: E402

from shared.infrastructure.connection.db_factory import raw_session_factory  # noqa: E402
from contexts.concept.infrastructure.persistence.repositories.concept_repository import (  # noqa: E402
    ConceptRepoImpl,
)
from contexts.concept.infrastructure.persistence.models.concept import (  # noqa: E402
    ConceptsDB,
    ConceptIndexTHDB,
    ConceptMemberDB,
)

MARK = "SMK9999"


async def main() -> int:
    async with raw_session_factory() as s:
        tx = await s.begin_nested()
        try:
            now = datetime.now(timezone.utc)

            # 1) 造概念
            concept = ConceptsDB(
                index_code=MARK,
                name="冒烟测试概念",
                concept_type="概念",
                source="ths",
                stock_count=1,
                is_active=True,
                first_seen_at=now,
            )
            s.add(concept)
            await s.flush()
            cid = concept.id

            # 2) 造成分股成员
            s.add(ConceptMemberDB(
                symbol=MARK,
                concept_id=cid,
                reason="冒烟原因",
                joined_at=now,
                synced_at=now,
                source="ths",
            ))

            # 3) 造两条日行情（验证 DISTINCT ON 取最新那条）
            for d, close in ((date(2026, 1, 5), 10.0), (date(2026, 1, 6), 12.0)):
                s.add(ConceptIndexTHDB(
                    index_code=MARK,
                    concept_name="旧名",
                    trade_date=d,
                    open=close, high=close, low=close, close=close,
                    volume=100, amount=1000.0,
                    change=close - 10.0, change_pct=(close - 10.0) / 10.0 * 100,
                    captured_at=now,
                ))
            await s.flush()

            repo = ConceptRepoImpl(s)

            # ── 验证 get_latest_closes：应取 2026-01-6（最新），name 用 concepts.name 覆盖
            closes = await repo.get_latest_closes([MARK])
            got = closes[MARK]
            print(f"get_latest_closes → trade_date={got['trade_date']} close={got['close']} "
                  f"concept_name={got['concept_name']!r}")
            assert got["trade_date"] == date(2026, 1, 6), "DISTINCT ON 未取最新交易日"
            assert got["close"] == 12.0, "取到了错误的行"
            assert got["concept_name"] == "冒烟测试概念", "COALESCE 未用 concepts.name 覆盖"

            # ── 验证 list_members：应拿到 1 行，字段齐全
            members = await repo.list_members(cid)
            print(f"list_members → {members}")
            assert len(members) == 1, f"应 1 行，实际 {len(members)}"
            m = members[0]
            assert m["symbol"] == MARK and m["reason"] == "冒烟原因"
            assert "name" in m, "缺 name 字段（COALESCE 结果）"

            # ── 验证 get_names
            names = await repo.get_names([MARK])
            print(f"get_names → {names}")
            assert names == {MARK: "冒烟测试概念"}

            # ── 验证 get_concept_by_id
            c = await repo.get_concept_by_id(cid)
            print(f"get_concept_by_id → {c.name if c else None}")
            assert c is not None and c.name == "冒烟测试概念"

            print("\n✅ JOIN / DISTINCT ON / COALESCE 全部验证通过（数据将回滚）")
            return 0
        finally:
            await tx.rollback()
            print("已回滚，未落盘")


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))