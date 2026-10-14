"""采集任务抽象基类、单元执行器、取消标志、交易日辅助

数据类与运行单元原样来自 step5/02 实现的 base，
已剥离：进度 / 收尾 / 增量查询（移入 runner + 端口）。
"""
from __future__ import annotations

import asyncio
import logging
from abc import ABC
from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any, Awaitable, Callable, ClassVar, Optional

if TYPE_CHECKING:
    from application.collect.context import CollectContext

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# 取消标志（兼容现状：模块级 set，单进程有效）
# ═══════════════════════════════════════════════════════════════════════════════

_cancel_flags: set[int] = set()


def request_cancel(task_id: int) -> None:
    """写入取消标志。被子类 run() 通过 is_cancelled() 检查。"""
    _cancel_flags.add(task_id)


def is_cancelled(task_id: int) -> bool:
    """检查 task_id 是否已收到取消信号。"""
    return task_id in _cancel_flags


def clear_cancel(task_id: int) -> None:
    """清理 task_id 的取消标志。runner 退出时自动调用。"""
    _cancel_flags.discard(task_id)


# ═══════════════════════════════════════════════════════════════════════════════
# 数据类（frozen，不可变）
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class UnitResult:
    """单个单元的执行结果，由 run() 通过 on_unit_done 上报"""

    success: bool
    detail: str = ""
    error: str | None = None
    skipped: bool = False
    saved_count: int = 0
    # collect_one 给业务调用方的结构化结果（如 KlineCollectResponse.model_dump()）
    data: Any = None


@dataclass(frozen=True)
class TaskSummary:
    """整个 run() 结束后的收尾汇报"""

    success: int
    fail: int
    skip: int = 0
    message: str = ""
    total_count: int = 0
    elapsed_ms: int = 0


class Cancelled(Exception):
    """子任务取消异常。子类 run() 内 raise 即可让框架收尾。"""


# ═══════════════════════════════════════════════════════════════════════════════
# 单元执行器（默认 run() 与概念任务共用）
# ═══════════════════════════════════════════════════════════════════════════════

RETRY_DELAY = 2.0


@dataclass
class UnitTally:
    success: int = 0
    fail: int = 0
    skip: int = 0
    saved: int = 0


async def run_units(
    task_id: int,
    units: list,
    label: Callable[[Any], str],
    work: Callable[[Any, Optional[float]], Awaitable[UnitResult]],
    on_unit_done,
    *,
    concurrency: int = 1,
    retry_delay: float = RETRY_DELAY,
) -> UnitTally:
    """逐单元执行 work(unit, delay)；抛异常的单元先挂起，主循环结束后以 delay=retry_delay 再试一轮

    - 首轮 delay=None；按 concurrency 分批并发
    - 挂起的单元在重试结束后才上报，避免进度被重复计数
    """
    tally = UnitTally()
    pending: list = []

    async def report(unit, result: UnitResult) -> None:
        if result.success:
            tally.success += 1
            tally.saved += result.saved_count
            if result.skipped:
                tally.skip += 1
        else:
            tally.fail += 1
        await on_unit_done(result, label(unit))

    async def attempt(unit) -> tuple[Optional[UnitResult], Optional[Exception]]:
        try:
            return await work(unit, None), None
        except Cancelled:
            raise
        except Exception as e:
            return None, e

    size = max(1, concurrency)
    for i in range(0, len(units), size):
        if is_cancelled(task_id):
            raise Cancelled()
        batch = units[i:i + size]
        outcomes = await asyncio.gather(*(attempt(u) for u in batch))
        for unit, (result, error) in zip(batch, outcomes):
            if error is not None:
                logger.debug("单元 %s 失败，稍后重试: %s", label(unit), error)
                pending.append(unit)
                continue
            await report(unit, result)

    if pending:
        logger.info("任务 %d：%d 个单元首轮失败，间隔 %.1fs 重试", task_id, len(pending), retry_delay)
    for unit in pending:
        if is_cancelled(task_id):
            raise Cancelled()
        try:
            result = await work(unit, retry_delay)
        except Cancelled:
            raise
        except Exception as e:
            logger.warning("单元 %s 重试仍失败: %s", label(unit), str(e)[:200])
            result = UnitResult(success=False, detail=label(unit), error=str(e)[:500])
        await report(unit, result)

    return tally


# ═══════════════════════════════════════════════════════════════════════════════
# 增量采集工具（mode=full / condition 时跳过库中已有单元）
# ═══════════════════════════════════════════════════════════════════════════════


def parse_date(value: Any) -> Optional[date]:
    """YYYYMMDD / YYYY-MM-DD / date → date"""
    if not value:
        return None
    if isinstance(value, date):
        return value
    s = str(value).replace("-", "")
    return date(int(s[:4]), int(s[4:6]), int(s[6:8]))


def resolve_trade_dates(params: dict) -> list[str]:
    """按 trade_date / start_date+end_date / days 解析交易日单元（YYYYMMDD，倒序）

    带 mode 时剔除周末（非交易日无数据，也永远不会"已存在"）。
    """
    trade_date = params.get("trade_date")
    if trade_date:
        return [str(trade_date).replace("-", "")]
    start = parse_date(params.get("start_date"))
    end = parse_date(params.get("end_date"))
    if not (start and end):
        end = date.today()
        start = end - timedelta(days=int(params.get("days", 1)) - 1)
    days = [end - timedelta(days=i) for i in range((end - start).days + 1)]
    if params.get("mode"):
        days = [d for d in days if d.weekday() < 5]
    return [d.strftime("%Y%m%d") for d in days]


# ═══════════════════════════════════════════════════════════════════════════════
# 抽象基类
# ═══════════════════════════════════════════════════════════════════════════════


class BaseCollectTask(ABC):
    """采集任务抽象基类

    子类契约：
      ① 必须设置类变量 name（与 registry 中的 task_type 一致）
      ② 实现 list_units(params) + collect_one(unit, params)，即可使用默认
         estimate_total / run（遍历单元、并发、失败重试一轮、上报进度）
      ③ 有特殊流程的任务可覆盖 estimate_total / run：
         - 每完成一个单元，立即调 on_unit_done(UnitResult, label)
         - 若需要取消，raise Cancelled() 让 framework 收尾

    可选钩子：
      - pre_execute(params): runner 开头调用一次
      - post_execute(params, summary): runner 收尾调用一次
    """

    # ── 任务标识（子类必须设置，与 registry 中的 task_type 一致） ──
    name: ClassVar[str] = ""

    # ── 元数据 ──
    facet: ClassVar[str] = ""
    sub_facet: ClassVar[str] = ""
    label: ClassVar[str] = ""
    status: ClassVar[str] = "ready"
    description: ClassVar[str] = ""
    sort_order: ClassVar[int] = 0

    # ── 执行配置 ──
    default_params: ClassVar[dict] = {}
    concurrency: ClassVar[int] = 1
    retry_delay: ClassVar[float] = RETRY_DELAY
    full_params: ClassVar[dict] = {}

    def __init__(self) -> None:
        # 由 runner 在调用 run() 之前注入
        self._task_id: int = -1
        self._ctx: Optional["CollectContext"] = None

    def bind(self, ctx: "CollectContext") -> None:
        """注册时由 registry 绑定 ctx（声明式任务写法不变）"""
        self._ctx = ctx

    @property
    def ctx(self) -> "CollectContext":
        if self._ctx is None:
            raise RuntimeError(
                f"{type(self).__name__} 未绑定 CollectContext（未经 setup_collect 注册）"
            )
        return self._ctx

    # ── 单元接口（子类实现）────────────────────────────────────────────

    async def list_units(self, params: dict) -> list[str]:
        """本次要跑的单元（股票代码 / 交易日 / ...）"""
        raise NotImplementedError(f"{type(self).__name__} 未实现 list_units")

    async def collect_one(self, unit: str, params: dict) -> UnitResult:
        """采一个单元并落库；失败抛异常"""
        raise NotImplementedError(f"{type(self).__name__} 未实现 collect_one")

    async def existing_units(self, units: list[str], params: dict) -> set[str]:
        """units 中库里已有数据的单元（带 mode 时跳过）；默认无"""
        return set()

    async def pending_units(self, params: dict) -> list[str]:
        """list_units 去掉已有单元（仅带 mode 时）"""
        units = await self.list_units(params)
        if not params.get("mode"):
            return units
        existing = await self.existing_units(units, params)
        return [u for u in units if u not in existing]

    @property
    def supports_collect_one(self) -> bool:
        return type(self).collect_one is not BaseCollectTask.collect_one

    # ── 默认实现（特殊流程的子类可覆盖）────────────────────────────────

    async def estimate_total(self, params: dict) -> int:
        """预估单元总数（runner 同步 await）"""
        return len(await self.pending_units(params))

    async def run(
        self,
        params: dict,
        on_unit_done: Callable[[UnitResult, str], Awaitable[None]],
    ) -> TaskSummary:
        """业务主循环；完成一个单元立即调用 on_unit_done(result, label)"""
        units = await self.pending_units(params)

        async def work(unit: str, delay: Optional[float]) -> UnitResult:
            if delay:
                await asyncio.sleep(delay)
            return await self.collect_one(unit, params)

        tally = await run_units(
            self._task_id, units, str, work, on_unit_done,
            concurrency=self.concurrency, retry_delay=self.retry_delay,
        )
        return TaskSummary(
            success=tally.success,
            fail=tally.fail,
            skip=tally.skip,
            total_count=len(units),
            message=self.summary_message(tally),
        )

    def summary_message(self, tally: UnitTally) -> str:
        return f"完成: 成功 {tally.success}（跳过 {tally.skip}），失败 {tally.fail}；写入 {tally.saved} 条"

    # ── 可选钩子 ────────────────────────────────────────────────────────

    async def pre_execute(self, params: dict) -> None:
        """预热钩子（默认空）"""

    async def post_execute(self, params: dict, summary: TaskSummary) -> None:
        """收尾钩子（默认空）"""


__all__ = [
    "BaseCollectTask",
    "Cancelled",
    "RETRY_DELAY",
    "TaskSummary",
    "UnitResult",
    "UnitTally",
    "clear_cancel",
    "is_cancelled",
    "parse_date",
    "request_cancel",
    "resolve_trade_dates",
    "run_units",
]
