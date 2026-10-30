"""采集 service 抽象：CollectResult + CollectService Protocol + BaseFetcher。

每个 collector 实现 collect() 即可（统一入口，HTTP 和调度都调它）。
限流/并发/入库在 collector 内自决，fetcher 只负责调 SDK。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar, Optional, Protocol

from pydantic import BaseModel

# 异常统一在 core.errors 定义（DomainError / RateLimited / SourceUnavailable / ...）
from core.errors import InvalidParams, NotSupported, RateLimited, SourceUnavailable


@dataclass(frozen=True)
class CollectResult:
    """一次采集执行的结果——调度日志和 HTTP 返回都用这个"""
    total: int = 0
    success: int = 0
    fail: int = 0
    skip: int = 0
    saved: int = 0
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "success": self.success,
            "fail": self.fail,
            "skip": self.skip,
            "saved": self.saved,
            "message": self.message,
        }


# ═══════════════════════════════════════════════════════════════════════
# Protocol
# ═══════════════════════════════════════════════════════════════════════


class CollectService(Protocol):
    """采集 service 抽象接口

    约束：
      ① name 必须全局唯一（用于 collect_logs.name 关联与前端目录展示）
      ② facet 必须是 tech / capital / fundamental / news / sentiment 之一
         （五数据面；**只有这一个维度**，没有 sub_facet 二级分组）
      ③ collect(params) 是统一入口：HTTP 透传和未来 collector 内部定时调度都调这个
      ④ RATE_LIMIT 用于 service 内部的限流（RedisCache.rate_limit 滑动窗口）
         格式: (source, max_count, window_seconds) 或 None
      ⑤ CONCURRENCY 用于 service 内部的并发（asyncio.Semaphore 容量）

    ⚠️ strategy 必须显式声明（见重构文档 §5.1）：
      运行时启发式推断会让 getattr(cls, "strategy", "") 永远取到空串，
      导致 collect_logs.kind 一直是 ''，审计信息完全丢失。

    ⚠️ strategy 与 QUERYABLE 是**正交**的两个维度：
      strategy 决定「怎么采」（前端表单 + 落库语义），
      QUERYABLE 决定「能不能实时直查」（/query 端点可用性）。
      ❌ 不要再用 kind='both' 表达「既能写又能读」——那会让
         daily_kline / stock_basic 这类 service 无法表达自己是增量还是全量。

    ❌ 已删除 DEFAULT_PARAMS：
      前端按 strategy 渲染表单——增量只给日期范围、全量只给一个按钮，
      不再渲染「用户可填参数」，所以 service 没有「默认参数表」这个概念。
      参数兜底一律写在 service 内部的 params.get("x", 默认值) 里。

    可选方法：
      get(...) → list[dict] | dict :  HTTP GET 入口（不走 collect），有则 QUERYABLE=True
      clear(params) → int :         全量覆盖前的清理钩子，默认 no-op
    """
    name: ClassVar[str]
    facet: ClassVar[str]
    label: ClassVar[str] = ""
    description: ClassVar[str] = ""

    # ── 采集方式（必须显式声明）──────────────────────
    # incremental : 增量，按 RANGE 描述的时间范围采集，区间内 upsert / 追加
    # full        : 全量采集（覆盖语义），一次性拉取并覆盖，清理模式见 CLEAR_MODE
    # realtime    : 实时直查，不入库（collect() 会被拒绝建任务）
    strategy: ClassVar[str] = "incremental"

    # ── 增量维度（仅 strategy='incremental' 需要）─────
    # {"start_key": "start_date", "end_key": "end_date", "granularity": "day"|"trade_day"}
    #   granularity='day'      : 区间自理型，service 内部处理起止，单次调用
    #   granularity='trade_day': 按交易日展开型，manager 拆成 N 个交易日逐日调用
    # ❌ strategy 为 full / realtime 时必须为 None
    RANGE: ClassVar[Optional[dict]] = None

    # ── 是否有实时直查入口（与 strategy 正交）────────
    QUERYABLE: ClassVar[bool] = False

    # ── 全量覆盖的清理模式 ─────────────────────────
    # none   : 只做自然键 upsert 覆盖，不删覆盖域外的残留（默认）
    # domain : 先删「覆盖域外残留」再写（需实现 clear()）
    CLEAR_MODE: ClassVar[str] = "none"

    # 目录中隐藏（前端不展示），如情绪面空壳占位
    hidden: ClassVar[bool] = False

    RATE_LIMIT: ClassVar[Optional[tuple[str, int, int]]] = None
    CONCURRENCY: ClassVar[int] = 1

    async def collect(self, params: dict) -> CollectResult:
        ...

    async def clear(self, params: dict) -> int:
        """全量覆盖前的清理钩子；默认 no-op。

        返回清理行数（计入任务 message）。
        ❌ 严禁无条件 TRUNCATE；必须按覆盖域窄化（trade_date / list_status / 主键集合）。
        ❌ clear() 与 collect() 必须是两次独立事务。
        ❌ 失败必须抛出 —— 禁止吞异常（否则产生「半清半写」的坏数据状态）。
        """
        return 0


__all__ = [
    "CollectResult", "CollectService", "BaseFetcher",
    "RateLimited", "SourceUnavailable", "InvalidParams", "NotSupported",
    "list_all_a_symbols",
    "list_all_concept_codes",
    "upsert_rows",
    "replace_rows_for_date",
    "delete_outside",
    "mark_outside",
    "chunk_rows_for_insert",
    "dedupe_rows",
    "fetch_with_retry",
    "PG_MAX_PARAMS",
    "PG_SAFE_PARAMS",
]


# ═══════════════════════════════════════════════════════════════════════
# 共享 helper：拉全 A 股票代码（list_status=L）— 多个 service 的"全量模式"用
# ═══════════════════════════════════════════════════════════════════════

async def list_all_a_symbols() -> list[str]:
    """从 tushare stock_basic 拉全 A 股票代码（list_status=L，6 位补零）

    用途：service.collect() 在 symbols 为空时（前端"全量采集"）走默认拉全 A。
    返回 [] 时表示 tushare 拉失败，调用方应给出明确错误。
    """
    import logging
    logger = logging.getLogger(__name__)
    try:
        from core.tushare_client import (
            get_tushare_client,
        )
        from core.tushare_utils import rows
        c = get_tushare_client()
        df = await c.query("stock_basic", list_status="L", fields="symbol")
        return [str(r["symbol"]).zfill(6) for r in rows(df) if r.get("symbol")]
    except Exception as e:
        logger.warning("list_all_a_symbols 失败: %r", e)
        return []


async def list_all_concept_codes() -> list[str]:
    """从 concept 表（concept_list 入库）拉全部 index_code

    用途：concept_members / concept_index_daily 全量模式。
    """
    import logging
    logger = logging.getLogger(__name__)
    try:
        from sqlalchemy import select
        from core.db import raw_session_factory
        from models.concept_compat import ConceptDB
        async with raw_session_factory() as session:
            rows_db = (await session.execute(
                select(ConceptDB.index_code)
            )).scalars().all()
            return [str(c) for c in rows_db if c]
    except Exception as e:
        logger.warning("list_all_concept_codes 失败: %r", e)
        return []


# ═══════════════════════════════════════════════════════════════════════
# 共享 helper：带重试 + 权限降级的上游调用
# ═══════════════════════════════════════════════════════════════════════

async def fetch_with_retry(fetch_fn, *, attempts: int = 3, rate_limit=None):
    """调上游 fetch，区分三类错误。

    ★ 返回值：
      - 正常 → ``(ok, items_or_none, message)``
      - 限流 → 退避重试，耗尽后抛 RateLimited
      - **权限不足** → 返回 ``(False, None, "该接口无权限…")``
        —— 账号级限制，重试无用 → service 应记为 **skip** 而不是 fail，
           任务终态仍是 done，避免「没权限」被误报成「采集失败」。
      - 其它故障 → 抛 SourceUnavailable

    ⚠️ 用法（service 内）：
        ok, items, msg = await fetch_with_retry(
            lambda: self._fetcher.fetch(trade_date=td), rate_limit=self.RATE_LIMIT)
        if not ok:
            return CollectResult(total=1, skip=1, message=msg)
    """
    import asyncio

    from core.errors import RateLimited, SourceNotPermitted
    from core.redis import check as _rl_check

    for attempt in range(attempts):
        if rate_limit is not None:
            await _rl_check(rate_limit)
        try:
            return True, await fetch_fn(), ""
        except RateLimited as e:
            if attempt < attempts - 1:
                await asyncio.sleep(e.retry_after)
            else:
                raise
        except SourceNotPermitted as e:
            # ★ 无权限 → 不重试（重试永远失败）
            return False, None, f"上游接口无访问权限，已跳过：{e}"
    return False, None, "重试耗尽"


# ═══════════════════════════════════════════════════════════════════════
# 共享 helper：幂等 upsert（多个 service 的落库逻辑复用）
# ═══════════════════════════════════════════════════════════════════════

# ★ PG 单条语句的参数上限（asyncpg 硬限制）。
#   官方文档：单个 prepared statement 最多 32767 个参数。
#   全市场日 K ≈ 5400 行 × 11 列 = 59,400 参数 → 直接超限报错：
#     "the number of query arguments cannot exceed 32767"
#   → 统一按「行数 × 列数 ≤ 安全值」分块。
PG_MAX_PARAMS = 32767
# 安全余量：留 10% 给 SQL 里其它占位符
PG_SAFE_PARAMS = int(PG_MAX_PARAMS * 0.9)   # ≈ 29490


def chunk_rows_for_insert(model, rows: list[dict]) -> list[list[dict]]:
    """按 PG 参数上限把 rows 切成若干块。

    每块参数量 = 行数 × 列数 ≤ PG_SAFE_PARAMS。
    """
    if not rows:
        return []
    ncols = max(len(r) for r in rows)
    per_chunk = max(1, PG_SAFE_PARAMS // max(1, ncols))
    return [rows[i:i + per_chunk] for i in range(0, len(rows), per_chunk)]


def dedupe_rows(rows: list[dict], conflict_cols: list[str]) -> list[dict]:
    """按冲突键去重（保留最后一条）。

    ★ 为什么必须去重：PG 的 ``ON CONFLICT DO UPDATE`` **不允许同一条语句内**
      出现两行拥有相同冲突键 —— 会报：
        "ON CONFLICT DO UPDATE command cannot affect row a second time"
      当上游返回重复行（如 Tushare 同一 symbol+end_date 多条 report_type=None
      的利润表、股东户数多期快照同键）时必然踩中。

    ★ 保留**最后**一条：上游返回通常是按时间递增，后面的更「新」。
    """
    if not rows or not conflict_cols:
        return rows
    seen: dict[tuple, dict] = {}
    for r in rows:
        key = tuple(r.get(c) for c in conflict_cols)
        seen[key] = r          # 后者覆盖前者
    return list(seen.values())


async def upsert_rows(
    model,
    rows: list[dict],
    conflict_cols: list[str],
    *,
    immutable_cols: list[str] | None = None,
) -> int:
    """在采集库（raw_data）做幂等 upsert，返回受影响行数。

    ★ 用 raw_session_factory —— 采集表一律在 raw_data 库。
    ★ 显式列出可更新列，不用 excluded 遍历全表（见规范 §4.5）。
    ★ conflict_cols 必须对应表上的唯一约束（幂等的前提）。
    ★ ★ 自动分块（PG 参数上限 32767）+ 自动按冲突键去重 —— 见上面两个 helper。
    """
    if not rows:
        return 0
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from core.db import raw_session_factory

    # 跳过主键/自增/时间戳列，以及冲突键本身
    skip = set(immutable_cols or []) | set(conflict_cols) | {"id", "created_at", "updated_at"}
    updatable = [c.name for c in model.__table__.columns if c.name not in skip]

    total = 0
    async with raw_session_factory() as session:
        for chunk in chunk_rows_for_insert(model, dedupe_rows(rows, conflict_cols)):
            stmt = pg_insert(model).values(chunk)
            update_cols = {name: stmt.excluded[name] for name in updatable}
            stmt = stmt.on_conflict_do_update(index_elements=conflict_cols, set_=update_cols)
            r = await session.execute(stmt)
            total += r.rowcount or 0
        await session.commit()
    return total


async def replace_rows_for_date(
    model,
    rows: list[dict],
    date_col: str,
    date_value,
    *,
    conflict_cols: list[str] | None = None,
) -> int:
    """「先删当日、再批量写入」模式（增量按交易日采集的标准动作）。

    ★ 分块写 —— 全市场单日数据行数多时参数会超 PG 上限。
    ★ 若给了 conflict_cols，则对写入批次按冲突键去重（防 DO UPDATE 二次命中）。
    """
    if not rows:
        return 0
    from sqlalchemy import delete
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from core.db import raw_session_factory

    total = 0
    async with raw_session_factory() as session:
        await session.execute(delete(model).where(getattr(model, date_col) == date_value))
        for chunk in chunk_rows_for_insert(
            model, dedupe_rows(rows, conflict_cols) if conflict_cols else rows
        ):
            stmt = pg_insert(model).values(chunk)
            r = await session.execute(stmt)
            total += r.rowcount or 0
        await session.commit()
    return total


async def delete_outside(
    model,
    keep_column: str,
    keep_values: list[str],
    *,
    where_extra=None,
) -> int:
    """删除「不在 keep_values 内」的残留行（全量覆盖的清理钩子）。

    ★ 必须窄化：keep_values 为空时**直接返回 0，不删任何东西**——
      否则一次上游返回空就会把整表清空（灾难性数据丢失）。
    ★ 返回删除行数。

    参数：
      model       : ORM 模型
      keep_column : 保留列名（如 'symbol'）
      keep_values : 本次采集覆盖到的键集合
      where_extra : 额外的窄化条件（如按 list_status 限定域）
    """
    if not keep_values:
        return 0
    from sqlalchemy import delete

    from core.db import raw_session_factory

    async with raw_session_factory() as session:
        cond = getattr(model, keep_column).notin_(keep_values)
        if where_extra is not None:
            cond = cond & where_extra
        r = await session.execute(delete(model).where(cond))
        await session.commit()
        return r.rowcount or 0


async def mark_outside(
    model,
    keep_column: str,
    keep_values: list[str],
    values: dict,
    *,
    where_extra=None,
) -> int:
    """把「不在 keep_values 内」的行**打标记**（不物理删除）。

    ★ 用于「退市」这类软语义：历史行情/财报仍按主键关联这些行，
      物理删除会产生孤儿行，把整条分析链路打断。
    ★ keep_values 为空时直接返回 0（绝不因为上游空返回就批量改状态）。
    ★ 返回受影响行数。
    """
    if not keep_values:
        return 0
    from sqlalchemy import update

    from core.db import raw_session_factory

    async with raw_session_factory() as session:
        cond = getattr(model, keep_column).notin_(keep_values)
        if where_extra is not None:
            cond = cond & where_extra
        r = await session.execute(update(model).where(cond).values(**values))
        await session.commit()
        return r.rowcount or 0


# ---- 以下原 infrastructure/fetcher/base.py（Fetcher 唯一职责：调 SDK 拿数） ----

class BaseFetcher(ABC):
    """Fetcher 抽象基类：调 SDK 拿数据，返回 list[BO]。不限流/不入库（service 里做）。"""
    # 数据源标识：'tushare' / 'adata' / 'pytdx' / 'eastmoney' / ...
    source: ClassVar[str] = ""
    # 业务类型标识：'daily_kline' / 'stock_basic' / ...
    fetcher_type: ClassVar[str] = ""
    # 元数据（可选，用于 admin 展示）
    label: ClassVar[str] = ""
    description: ClassVar[str] = ""

    @abstractmethod
    async def fetch(self, **params) -> list[BaseModel]:
        """调 SDK 拿数据，返回 list[BO]（Pydantic BaseModel 子类）

        入参直接 kwargs，service 负责类型校验和默认值填充。
        """
        ...
