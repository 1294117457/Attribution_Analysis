"""按 (symbol, trade_date) 维度仓储的通用 upsert/find_by_symbol 实现。

抽取 8 个 cap_* / fin_top10_* / base_*（SymboledDatedEntity）仓储中共用的
批量 upsert + 按 symbol 查询逻辑，避免每个仓库复制一遍。

字段筛选约定：UK 列（symbol, trade_date[, ann_date, holder_name] 等）外
的"业务字段"由各仓库自己声明（区别在于不允许覆盖时间戳/UK 主键列）。

不抽到 base 的原因：仓库层要兼顾"读侧查询条件"的多样性（如按 end_date
查询股东户数、按 holder_name 模糊查询等），抽完反而引入大量 override。

配套设计文档：docs/dev/step2/04collection-plan/01-stock-fetcher-detail.md
"""

from __future__ import annotations

from typing import Generic, Iterable, Optional, TypeVar

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


def chunks(items: list, size: int) -> Iterable[list]:
    for i in range(0, len(items), size):
        yield items[i:i + size]


def _build_row_dict(entity: object, columns: list[str]) -> dict:
    """从 entity 抽取 columns 中存在的字段值"""
    out: dict = {}
    for col in columns:
        if hasattr(entity, col):
            out[col] = getattr(entity, col)
    return out


def _dedupe_by_key(entities: list, key_columns: list[str]) -> list:
    """按 UK 列去重，同批保留最后一条

    PG 的 `ON CONFLICT DO UPDATE` 不允许一条 INSERT 语句里出现两行
    相同的冲突键（CardinalityViolationError）。tushare 的股东户数 / 分红
    等接口对同一 (symbol, end_date) 会返回多条记录，这里在写库前折叠掉，
    保留最后一条（后到的通常是最新披露口径）。
    """
    seen: dict = {}
    for e in entities:
        try:
            k = tuple(getattr(e, c) for c in key_columns)
        except AttributeError:
            k = (id(e),)  # entity 缺 key 字段时不去重，交由 DB 报错
        seen[k] = e
    return list(seen.values())


async def save_batch_symboled_dated(
    session: AsyncSession,
    model_cls: type,
    entities: list,
    value_columns: list[str],
    constraint_name: str,
    batch_size: int = 500,
    key_columns: Optional[list[str]] = None,
) -> int:
    """通用 (symbol, trade_date) 维度 upsert 工具

    Args:
        session: SQLAlchemy 异步 session（调用方负责 commit）
        model_cls: ORM 模型类
        entities: 实体列表
        value_columns: 要写入的业务列（不含 id / 时间戳 / UK 列）
        constraint_name: ON CONFLICT 使用的约束名
        batch_size: 单批条数（默认 500）
        key_columns: UK 主键列，必须一并 INSERT。
            ON CONFLICT 依赖 UK 列定位冲突行，若不写入则 symbol/trade_date
            全为 NULL —— 轻则 not-null 违约，重则所有行挤进同一条 (NULL,NULL)。
            为 None 时自动取 (symbol, trade_date)。

    Returns:
        实际写入的条数（按 batch 累加）
    """
    if not entities:
        return 0
    excluded = pg_insert(model_cls).excluded
    # ON CONFLICT 的 set_ 只更新业务列；UK 列必须由 INSERT 阶段提供，
    # 否则 upsert 无法定位冲突行（历史 bug：symbol/trade_date 漏写导致全表 NULL）
    upsert_set = {col: getattr(excluded, col) for col in value_columns}
    keys = list(key_columns or ["symbol", "trade_date"])
    insert_columns = list(dict.fromkeys([*keys, *value_columns]))

    total = 0
    for batch in chunks(_dedupe_by_key(entities, keys), batch_size):
        rows = [_build_row_dict(e, insert_columns) for e in batch]
        stmt = (
            pg_insert(model_cls)
            .values(rows)
            .on_conflict_do_update(
                constraint=constraint_name,
                set_=upsert_set,
            )
        )
        result = await session.execute(stmt)
        total += result.rowcount or len(batch)
    await session.commit()
    return total


async def find_by_symbol_and_date_range(
    session: AsyncSession,
    model_cls: type,
    symbol: str,
    start_date_attr: Optional[str] = None,
    end_date_attr: Optional[str] = None,
    date_col: str = "trade_date",
    extra_filters: Optional[list] = None,
    order_desc: bool = True,
    limit: Optional[int] = None,
) -> list:
    """通用按 symbol + 日期范围查询"""
    stmt = select(model_cls).where(getattr(model_cls, "symbol") == symbol)
    if start_date_attr is not None:
        stmt = stmt.where(getattr(model_cls, date_col) >= start_date_attr)
    if end_date_attr is not None:
        stmt = stmt.where(getattr(model_cls, date_col) <= end_date_attr)
    if extra_filters:
        stmt = stmt.where(*extra_filters)
    order_col = getattr(model_cls, date_col)
    stmt = stmt.order_by(order_col.desc() if order_desc else order_col.asc())
    if limit:
        stmt = stmt.limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())