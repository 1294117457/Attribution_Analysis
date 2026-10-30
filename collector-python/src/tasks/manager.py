"""后台任务执行器：建任务立即返回，后台按交易日循环调现有 service.collect()。

设计约束（不碰 schedule、不改 collector 实现）：
  - 每个 service 的 collect(params) 一行不动，复用其内部限流/并发/入库
  - 进度放 Redis Hash（collect:task:{id}，TTL 7 天），Java 不引入 Redis 客户端，只透传
  - TASKS 仅进程内持有 asyncio.Task 句柄（单 worker 部署，见 Dockerfile --workers 1）
  - 日志三态写 PG collect_logs（attribution 库），中间进度只写 Redis
  - 采集方式由 service 的 strategy 类属性声明；请求体的 strategy 与之必须一致
  - 区间展开规则（按 service 的 RANGE 声明决定，不硬编码名单）：
      granularity=trade_day → 按交易日展开（start_date/end_date 区间 → 每天调一次）
      granularity=day       → service 内部已处理区间，单次调用
      RANGE=None（full/realtime/无维度增量）→ 单次调用

规范见 backend-java/docs/开发文档/采集模块/采集模块重构开发文档.md §5
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import date, datetime, timedelta, timezone

from collectors import BY_NAME
from core.errors import CollectorNotFound, InvalidParams
from core.redis import get_redis
from tasks import log_repo

logger = logging.getLogger(__name__)

TASK_KEY_PREFIX = "collect:task:"
TASK_LIST_KEY = "collect:tasks"      # 最近任务 id（ltrim  capped）
TASK_LIST_MAX = 200
TASK_TTL_SECONDS = 7 * 24 * 3600
MAX_RANGE_DAYS = 366
CANCEL_KEY_PREFIX = "collect:cancel:"  # 中断标记（跨进程生效）
CANCEL_TTL_SECONDS = 3600

# strategy 白名单（与 collect_logs.kind 的 CHECK 约束一致）
_VALID_STRATEGIES: frozenset[str] = frozenset({"incremental", "full"})

# 旧前端兼容：mode → strategy 映射（condition 的旧语义就是「按条件采」= 增量）
_LEGACY_MODE_MAP: dict[str, str] = {"condition": "incremental", "full": "full"}

TASKS: dict[str, asyncio.Task] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_day(value, key: str) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    s = str(value).strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        raise InvalidParams(f"{key} 非法，期望 YYYY-MM-DD：{value!r}")


async def _trading_days(start: date, end: date) -> list[date]:
    """区间内交易日。

    ★ 三级降级（任一级成功即返回）：
      ① 读本地表 ``tech_trade_cal``（raw_data 库）—— 采集过就有，最快、零上游成本
      ② 上游 Tushare ``trade_cal`` —— 本地表**覆盖不全**/读失败时兜底（需要接口权限）
      ③ 自然日展开（周一~周五）—— 上游也不可用时的最后兜底

    ⚠️ 必须用 raw_session_factory()：tech_trade_cal 属采集库（raw_data），
       用 db_session_factory() 会连到业务库（attribution）→ 表不存在。
    """
    days = await _trading_days_from_db(start, end)
    if days:
        return days

    days = await _trading_days_from_upstream(start, end)
    if days:
        return days

    logger.warning(
        "交易日历不可用（本地表覆盖不全 + 上游失败），回退自然日展开 %s~%s", start, end)
    out: list[date] = []
    d = start
    while d <= end:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


# ★ 公开别名：service 的 expand_calls 钩子也要用同一个交易日历实现
#   （否则 service 与 manager 的展开口径会不一致 → 分母对不上）
trading_days_between = _trading_days


async def _trading_days_from_db(start: date, end: date) -> list[date]:
    """从本地 tech_trade_cal 表读交易日（覆盖不全返回 []）。

    ★ ⚠️ **必须要求「逐日全覆盖」**（不能只看比例）：
      日历表是**按需回写**的（只存被查过的区间），所以覆盖范围天然是碎片化的。
      若只按比例判断（例如「覆盖 87% 就信」），区间尾部缺失的日期会被
      **静默丢弃** → 那些交易日永远不会被采集，`progress` 的分母也偏小。
      实测踩坑：本地表覆盖 10-24~11-05（13/15 天 = 87% > 80% 阈值），
      结果 11-06、11-07 两个交易日被静默跳过。

      → 正确做法：要求区间内**每一天**都有日历行（含 `is_open=False` 的休市日），
        否则判定覆盖不全 → 改走上游补齐。
    """
    try:
        from sqlalchemy import select

        from core.db import raw_session_factory
        from models.mkt_calendar import MktCalendarDB

        async with raw_session_factory() as session:
            rows = (
                await session.execute(
                    select(MktCalendarDB.cal_date)
                    .where(MktCalendarDB.cal_date.between(start, end))
                    .distinct()
                )
            ).scalars().all()
            covered = {d for d in rows if d}

        span_days = (end - start).days + 1
        if len(covered) < span_days:
            missing = span_days - len(covered)
            logger.info(
                "交易日历本地表覆盖不全（%d/%d 天，缺 %d 天），改走上游",
                len(covered), span_days, missing)
            return []

        # ★ 覆盖完整 → 取开市日
        async with raw_session_factory() as session:
            open_rows = (
                await session.execute(
                    select(MktCalendarDB.cal_date)
                    .where(
                        MktCalendarDB.cal_date.between(start, end),
                        MktCalendarDB.is_open.is_(True),
                    )
                    .distinct()
                    .order_by(MktCalendarDB.cal_date)
                )
            ).scalars().all()
            return [d for d in open_rows if d]
    except Exception as e:
        logger.warning("交易日历本地表读取失败：%r", e)
        return []


async def _trading_days_from_upstream(start: date, end: date) -> list[date]:
    """从 Tushare trade_cal 拉交易日（失败/无权限返回 []）。

    ★ 为什么要这一级：``tech_trade_cal`` 表**默认是空的**（没有任何 collector 往里写），
      只靠本地表会让区间展开退化成「周一~周五」→ 法定节假日被当成交易日，
      白跑一次上游调用（返回空），还会让 progress 的分母虚高。
      → 上游这一级保证「法定节假日也跳过」。

    ⚠️ trade_cal 单次跨度约 1 年上限 → 按年切段查询。
    """
    try:
        from core.tushare_client import get_tushare_client
        from core.tushare_utils import rows as df_rows

        client = get_tushare_client()
        out: list[date] = []
        # ★ 收集区间内**全部**日历行（含休市日）→ 回写本地表，
        #   这样本地表的覆盖度校验才能通过（否则只有 is_open=True 的行，
        #   覆盖天数 = 交易日数 ≈ 自然天数的 70% → 判定为「覆盖不足」→ 每次都问上游）
        all_rows: list[tuple[date, bool]] = []
        seg_start = date(start.year, 1, 1)
        while seg_start <= end:
            seg_end = date(seg_start.year, 12, 31)
            if seg_end > end:
                seg_end = end
            df = await client.query(
                "trade_cal",
                start_date=seg_start.strftime("%Y%m%d"),
                end_date=seg_end.strftime("%Y%m%d"),
                exchange="SSE",
            )
            for r in df_rows(df):
                d = _parse_day(r.get("cal_date"), "cal_date")
                if d is None or not (start <= d <= end):
                    continue
                is_open = bool(r.get("is_open"))
                all_rows.append((d, is_open))
                if is_open:
                    out.append(d)
            seg_start = date(seg_start.year + 1, 1, 1)
        days = sorted(set(out))
        if all_rows:
            # ★ 回写本地表：下次展开直接命中本地表（零上游成本）
            await _save_calendar_to_db(all_rows)
        return days
    except Exception as e:
        logger.warning("交易日历上游拉取失败：%r", e)
        return []


async def _save_calendar_to_db(rows: list[tuple[date, bool]]) -> None:
    """把日历行（开市 + 休市）写回本地 tech_trade_cal 表（best-effort）。

    ★ 目的：把「每次建任务都要问上游要交易日」变成「一次问、长期复用」。
    ⚠️ 表的 UK 是 (cal_date, exchange) → 幂等 upsert。
    ⚠️ **休市日也要写入**（is_open=False）—— 覆盖度校验要求「区间内每一天都有日历行」，
       缺了休市日会导致本地表被误判为「覆盖不全」→ 每次都问上游。
    ⚠️ 用 DO UPDATE 而非 DO NOTHING：上游的 `is_open` 可能与旧值不同
       （例如临时休市调整），DO NOTHING 会让旧值**永久留存** → 交易日判定错误。
    """
    try:
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        from core.db import raw_session_factory
        from models.mkt_calendar import MktCalendarDB

        payload = [
            {
                "exchange": "SSE",
                "cal_date": d,
                "is_open": is_open,
                "data_source": "tushare",
            }
            for d, is_open in rows
        ]
        async with raw_session_factory() as session:
            for i in range(0, len(payload), 500):
                chunk = payload[i:i + 500]
                stmt = pg_insert(MktCalendarDB).values(chunk)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["cal_date", "exchange"],
                    set_={
                        "is_open": stmt.excluded["is_open"],
                        "data_source": stmt.excluded["data_source"],
                    },
                )
                await session.execute(stmt)
            await session.commit()
    except Exception as e:
        logger.warning("交易日历回写本地表失败（忽略）：%r", e)


async def _expand(cls, params: dict) -> list[dict]:
    """把一次任务请求展开为一次或多次 collect(params) 调用参数。

    ★ 区间展开的唯一实现点——其他地方不得重复实现日期展开。
    ★ 依据 service 的 RANGE 声明（不再靠 DEFAULT_PARAMS 隐式约定）。
    """
    rng = getattr(cls, "RANGE", None)
    if not rng:
        # 无增量维度（full / realtime / 无维度增量）→ 单次调用
        # 传了日期参数也直接忽略（full 的覆盖域由 service 的 clear() 自行界定）
        return [dict(params)]

    start_key = rng.get("start_key", "start_date")
    end_key = rng.get("end_key", "end_date")
    granularity = rng.get("granularity", "day")
    start = _parse_day(params.get(start_key), start_key)
    end = _parse_day(params.get(end_key), end_key)
    trade = _parse_day(params.get("trade_date"), "trade_date")

    if granularity == "trade_day":
        # 按交易日展开型：区间 → 逐个交易日调一次
        if trade is not None and (start is not None or end is not None):
            raise InvalidParams("trade_date 不能与区间参数同传")
        if start is not None or end is not None:
            start = start or end
            end = end or start
            assert start is not None and end is not None
            if start > end:
                raise InvalidParams("start_date 不能晚于 end_date")
            if (end - start).days > MAX_RANGE_DAYS:
                raise InvalidParams(f"日期范围最多 {MAX_RANGE_DAYS} 天")
            base = {k: v for k, v in params.items()
                    if k not in (start_key, end_key, "trade_date")}
            return [{**base, "trade_date": d.isoformat()}
                    for d in await _trading_days(start, end)]
        if trade is not None:
            base = {k: v for k, v in params.items() if k != "trade_date"}
            return [{**base, "trade_date": trade.isoformat()}]
        # 都不传：与各 service「默认今天」行为一致
        return [{**params, "trade_date": date.today().isoformat()}]

    # granularity == "day"：区间自理型 → service 内部处理起止，单次调用
    if start is not None and end is not None:
        if start > end:
            raise InvalidParams("start_date 不能晚于 end_date")
        if (end - start).days > MAX_RANGE_DAYS:
            raise InvalidParams(f"日期范围最多 {MAX_RANGE_DAYS} 天")
    if trade is not None and (start is not None or end is not None):
        raise InvalidParams("trade_date 不能与区间参数同传")

    # ★ service 自定义展开钩子（可选）
    #   有些 service 声明 granularity='day'（区间自理），但**同时**支持按天拆分
    #   以获得可见的进度刻度（如 daily_kline：全市场按日整批采集）。
    #   service 只需实现 `async def expand_calls(self, params) -> list[dict] | None`，
    #   返回 None 表示「沿用默认单步语义」。
    # ⚠️ 钩子是**实例方法**（要 self）→ 必须先实例化再调用；
    #   service 构造是廉价的（无 IO），不会带来额外开销。
    hook = getattr(cls, "expand_calls", None)
    if callable(hook):
        try:
            calls = await hook(cls(), params)
        except InvalidParams:
            raise
        except Exception as e:  # noqa: BLE001 — 钩子失败不该让任务建不起来
            logger.warning("service %s 的 expand_calls 钩子失败，回退单步：%r",
                           getattr(cls, "name", "?"), e)
            calls = None
        if calls:
            return calls

    return [dict(params)]


def _resolve_strategy(cls, raw_strategy: str | None) -> str:
    """解析本次任务的有效采集方式，并与 service 声明做一致性校验。

    优先级：请求体的 strategy → 旧 mode 映射 → service 声明的 strategy。
    抛 InvalidParams 表示不合法（→ HTTP 400）。
    """
    declared = (getattr(cls, "strategy", "") or "incremental").strip()
    raw = (raw_strategy or "").strip()

    # ⓪ 实时查询服务不支持建任务（先判，避免后续校验给出误导性错误）
    if declared == "realtime":
        raise InvalidParams(f"{cls.name} 是实时查询服务，不支持后台任务（请调 query）")

    # ① 旧 mode 兼容：condition/full → incremental/full
    if raw in _LEGACY_MODE_MAP:
        raw = _LEGACY_MODE_MAP[raw]

    # ② 缺省 → 用 service 声明兜底
    if not raw:
        raw = declared

    # ③ 值域校验
    if raw not in _VALID_STRATEGIES:
        raise InvalidParams(f"strategy 仅支持 {sorted(_VALID_STRATEGIES)}")

    # ④ 与 service 声明的一致性（service 可通过 ALLOW_* 放宽）
    if raw != declared:
        allow_other = (
            (raw == "full" and getattr(cls, "ALLOW_FULL", False))
            or (raw == "incremental" and getattr(cls, "ALLOW_INCREMENTAL", False))
        )
        if not allow_other:
            raise InvalidParams(
                f"{cls.name} 声明的采集方式是 {declared}，不接受 {raw}"
            )
    return raw


async def _cancel_requested(task_id: str) -> bool:
    """检查是否收到中断请求（Redis 标记，跨进程生效）。"""
    try:
        redis = await get_redis()
        return bool(await redis.exists(CANCEL_KEY_PREFIX + task_id))
    except Exception:
        return False


async def _run(task_id: str, cls, calls: list[dict], strategy: str) -> None:
    """执行 N 步。

    ★ 计数器口径（见规范 §7.2）：
      success/fail/done 是**步数**（一次 collect() 调用 = 1 步），
      saved_total 是**行数**。
      绝不透传 CollectResult.total/success/fail/skip——
      那些字段的语义在 28 个 collector 之间不一致，透传会让审计量纲漂移。
    """
    key = TASK_KEY_PREFIX + task_id
    redis = await get_redis()
    await log_repo.mark_running(task_id)
    started = datetime.now(timezone.utc)
    success = fail = saved_total = 0
    skipped = 0
    cleared_total = 0
    last_msg = ""
    detail: list[dict] = []
    # ★ 全量覆盖：先清覆盖域外残留，再写
    use_clear = strategy == "full" and (getattr(cls, "CLEAR_MODE", "none") or "none") == "domain"
    try:
        await redis.hset(key, mapping={"status": "running",
                                       "started_at": _now_iso(),
                                       "updated_at": _now_iso()})
        for i, p in enumerate(calls, 1):
            # ★ 软中断：每步开头检查 Redis 标记，当前步做完再停（数据完整，可续跑）
            # 用 CancelledError 跳出 → 走下面的 except asyncio.CancelledError 分支落终态
            if await _cancel_requested(task_id):
                raise asyncio.CancelledError()
            step_ok = False
            step_skipped = False
            step_msg = ""
            try:
                # ★ 同一 service 实例贯穿 clear + collect：
                #   这样 service 可以在实例上缓存上游结果集，
                #   clear() 与 collect() 不必各拉一次上游（省一半配额）。
                svc = cls()
                # ① 全量覆盖：先清理（失败必须抛出 → 本步失败，不产生半清半写）
                if use_clear:
                    cleared = await svc.clear(p)
                    cleared_total += int(cleared or 0)
                # ② 采集
                res = await svc.collect({**p, "strategy": strategy})
                step_ok = True
                # 只取行数（saved）——步数由本函数自己判定
                saved_total += int(getattr(res, "saved", 0) or 0)
                # ★ skip：service 明确说「这步跳过了」（如非交易日无数据）
                #   → 计入 skip，不计入 success/fail（不影响任务成败判定）
                if int(getattr(res, "skip", 0) or 0) > 0:
                    step_skipped = True
                step_msg = (getattr(res, "message", "") or "")[:500]
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001 — 单步失败记账，继续跑剩余天
                step_msg = f"第 {i}/{len(calls)} 步异常：{e!r}"
                logger.exception("任务 %s 第 %d 步异常", task_id, i)
            # ★ 步数口径：一次调用 = 1 步，成功即 success
            if step_ok:
                success += 1
                if step_skipped:
                    skipped += 1
            else:
                fail += 1
            last_msg = step_msg
            detail.append({"step": i, "ok": step_ok, "message": step_msg[:500]})
            await redis.hset(key, mapping={
                "done": i, "success": success, "fail": fail, "skip": skipped,
                "saved_total": saved_total, "message": last_msg[:500],
                # progress = 0-100，与 collect_logs.progress 同口径
                "progress": int(i * 100 / len(calls)) if calls else 100,
                "updated_at": _now_iso(),
            })
        status = "done" if fail < len(calls) else "failed"
        final_msg = (f"共 {len(calls)} 步，成功 {success}，失败 {fail}，"
                     + (f"跳过 {skipped}，" if skipped else "")
                     + f"写入 {saved_total} 行。"
                     + (f"覆盖前清理 {cleared_total} 行。" if cleared_total else "")
                     + f"{last_msg}")[:800]
        duration_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        await redis.hset(key, mapping={
            "status": status, "finished_at": _now_iso(),
            "updated_at": _now_iso(), "message": final_msg,
        })
        await log_repo.mark_finished(
            task_id, status=status, done=len(calls),
            success=success, fail=fail, skip=skipped, saved_total=saved_total,
            message=final_msg, detail=detail, duration_ms=duration_ms,
            total_steps=len(calls))
    except asyncio.CancelledError:
        # 🔴 CancelledError 不是 Exception，必须单独捕获，且必须写在 except Exception 之前
        logger.info("任务 %s 被中断", task_id)
        cancelled_msg = f"用户中断（已完成 {success + fail}/{len(calls)} 步）"[:800]
        duration_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        # 已被取消的任务里 await 可能再次抛 CancelledError → 用 BaseException 兜住，
        # 保证终态能落库（否则 collect_logs 会永远停在 running）
        try:
            await redis.hset(key, mapping={"status": "cancelled", "finished_at": _now_iso(),
                                           "updated_at": _now_iso(), "message": cancelled_msg})
        except BaseException:  # noqa: BLE001 — 取消路径不允许再抛
            pass
        try:
            await log_repo.mark_cancelled(
                task_id, done=success + fail, success=success, fail=fail,
                skip=skipped, saved_total=saved_total, message=cancelled_msg,
                total_steps=len(calls))
        except BaseException:  # noqa: BLE001 — 取消路径不允许再抛
            logger.error("任务 %s 中断终态落库失败", task_id, exc_info=True)
        raise            # ← 必须重新抛出，保持 asyncio 的取消语义
    except Exception as e:  # noqa: BLE001 — 任务级兜底
        logger.exception("任务 %s 执行异常", task_id)
        err_msg = f"任务异常：{e!r}"[:800]
        duration_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        try:
            await redis.hset(key, mapping={"status": "failed",
                                           "finished_at": _now_iso(),
                                           "updated_at": _now_iso(),
                                           "message": err_msg})
        except BaseException:  # noqa: BLE001
            pass
        try:
            await log_repo.mark_finished(
                task_id, status="failed", done=success + fail, success=success, fail=fail + 1,
                skip=skipped, saved_total=saved_total, message=err_msg, error=err_msg,
                detail=detail, duration_ms=duration_ms, total_steps=len(calls))
        except BaseException:  # noqa: BLE001 — 兜底路径不允许再抛
            logger.error("任务 %s 失败终态落库失败", task_id, exc_info=True)
    finally:
        # ⚠️ finally 里的 await 在「已被取消」的任务中可能再抛 CancelledError，
        # 会跳过后续清理 → 必须逐项 try/except 包住，不能共用一个 try。
        try:
            await redis.expire(key, TASK_TTL_SECONDS)
        except BaseException:  # noqa: BLE001
            pass
        # 清理中断标记
        try:
            await redis.delete(CANCEL_KEY_PREFIX + task_id)
        except BaseException:  # noqa: BLE001
            pass
        TASKS.pop(task_id, None)


async def create_task(
    facet: str,
    name: str,
    strategy: str,
    params: dict,
    trigger_source: str = "manual",
    parent_task_id: str | None = None,
) -> dict:
    """建任务并后台启动。

    抛 CollectorNotFound → 404；抛 InvalidParams → 400。
    """
    cls = BY_NAME.get(name)
    if cls is None or cls.facet != facet:
        raise CollectorNotFound(f"collector {facet}/{name} 不存在")

    # ★ strategy 解析 + 与 service 声明的一致性校验（权威判定）
    strategy = _resolve_strategy(cls, strategy)

    # ★ full 不走区间展开（覆盖是 1 步）；incremental 按 RANGE 展开
    if strategy == "full":
        calls = [dict(params or {})]
    else:
        calls = await _expand(cls, dict(params or {}))
        if not calls:  # _trading_days 在全休市区间可能为空
            raise InvalidParams("区间内无交易日，无需执行")

    task_id = uuid.uuid4().hex[:16]
    key = TASK_KEY_PREFIX + task_id
    redis = await get_redis()
    range_start, range_end = log_repo.describe_range(dict(params or {}), calls)
    # 🔴 insert_queued 失败会抛出 → 不受理任务（落审计账是受理的核心动作）
    await log_repo.insert_queued(
        task_id=task_id, facet=facet, name=name,
        # ★ kind 列承载「本次执行的采集方式」；mode 语义收敛为「编排来源」
        kind=strategy,
        mode="manual",
        params=dict(params or {}),
        range_start=range_start, range_end=range_end, total=len(calls),
        trigger_source=trigger_source, trigger_user=None,
        parent_task_id=parent_task_id,
    )
    await redis.hset(key, mapping={
        "task_id": task_id, "facet": facet, "name": name,
        "kind": strategy,
        "strategy": strategy,
        "mode": "manual",
        "params_json": json.dumps(params or {}, ensure_ascii=False, default=str),
        "status": "queued", "total": len(calls), "done": 0,
        "success": 0, "fail": 0, "skip": 0, "saved_total": 0, "message": "排队中",
        "created_at": _now_iso(), "updated_at": _now_iso(),
    })
    await redis.expire(key, TASK_TTL_SECONDS)
    await redis.lpush(TASK_LIST_KEY, task_id)
    await redis.ltrim(TASK_LIST_KEY, 0, TASK_LIST_MAX - 1)

    TASKS[task_id] = asyncio.create_task(_run(task_id, cls, calls, strategy))
    logger.info("采集任务已创建 %s %s/%s 共 %d 步 strategy=%s",
                task_id, facet, name, len(calls), strategy)
    return {"task_id": task_id, "status": "queued", "total": len(calls),
            "strategy": strategy}


async def get_task_state(task_id: str) -> dict | None:
    """读任务进度；不存在/过期返回 None。"""
    redis = await get_redis()
    raw = await redis.hgetall(TASK_KEY_PREFIX + task_id)
    if not raw:
        return None

    def _int(v, default: int = 0) -> int:
        try:
            return int(v)
        except (TypeError, ValueError):
            return default

    params: dict = {}
    try:
        params = json.loads(raw.get("params_json") or "{}")
    except (json.JSONDecodeError, TypeError):
        pass
    return {
        "task_id": raw.get("task_id", task_id),
        "facet": raw.get("facet", ""),
        "name": raw.get("name", ""),
        # ★ strategy 是新契约字段；kind 为灰度兼容（同义）
        "strategy": raw.get("strategy") or raw.get("kind", ""),
        "kind": raw.get("kind", ""),
        "mode": raw.get("mode", ""),
        "params": params,
        "status": raw.get("status", ""),
        "total": _int(raw.get("total")),
        "done": _int(raw.get("done")),
        "success": _int(raw.get("success")),
        "fail": _int(raw.get("fail")),
        "skip": _int(raw.get("skip")),
        "saved_total": _int(raw.get("saved_total")),
        "progress": _int(raw.get("progress")),
        "message": raw.get("message", ""),
        "created_at": raw.get("created_at", ""),
        "started_at": raw.get("started_at", ""),
        "updated_at": raw.get("updated_at", ""),
        "finished_at": raw.get("finished_at", ""),
    }


async def cancel_task(task_id: str) -> bool:
    """请求中断任务。写 Redis 标记（软中断：当前步做完再停）。

    返回 False 表示任务不存在或已结束。

    ⚠️ 为什么**不**直接 task.cancel()：
    硬 cancel 会在 collect() 执行到一半时抛 CancelledError，
    而 collect() 内部可能正处在「DELETE 当日 + INSERT 新数据」的写库中间，
    中途取消会让当日数据既没删干净也没写全 —— 数据比「任务多跑一会儿」糟糕得多。
    软中断（每步开头查 Redis 标记）保证数据完整，代价是当前步跑完才停。
    """
    redis = await get_redis()
    # ① 先看任务是否还在
    state = await get_task_state(task_id)
    if not state or state.get("status") not in ("queued", "running"):
        return False

    # ② 写中断标记（跨进程生效，这是关键；_run 每步开头会检查它）
    await redis.set(CANCEL_KEY_PREFIX + task_id, "1", ex=CANCEL_TTL_SECONDS)

    # ③ 标记审计字段
    await log_repo.mark_cancel_requested(task_id)
    return True


__all__ = ["create_task", "get_task_state", "cancel_task", "recover_stale_tasks", "TASKS",
           "TASK_KEY_PREFIX", "TASK_LIST_KEY", "CANCEL_KEY_PREFIX", "MAX_RANGE_DAYS",
           "trading_days_between"]


async def recover_stale_tasks() -> int:
    """重启恢复：running/queued → failed（Redis + collect_logs 双写）。

    依据 Redis capped list `collect:tasks` 前 200 个 id，无需 SCAN。
    返回置为 failed 的任务数。
    """
    from tasks import log_repo as _log_repo

    try:
        redis = await get_redis()
        ids = await redis.lrange(TASK_LIST_KEY, 0, TASK_LIST_MAX - 1) or []
    except Exception as e:
        logger.warning("重启恢复读取任务列表失败: %r", e)
        return 0
    now = _now_iso()
    recovered = 0
    for raw_tid in ids:
        task_id = str(raw_tid)
        try:
            state = await get_task_state(task_id)
        except Exception:
            continue
        if not state or state.get("status") not in ("queued", "running"):
            continue
        prev_msg = str(state.get("message") or "")
        message = (prev_msg + "；服务重启中断，已终止" if prev_msg else "服务重启中断，已终止")[:800]
        try:
            await redis.hset(TASK_KEY_PREFIX + task_id, mapping={
                "status": "failed", "finished_at": now,
                "updated_at": now, "message": message,
            })
            await redis.expire(TASK_KEY_PREFIX + task_id, TASK_TTL_SECONDS)
        except Exception as e:
            logger.warning("重启恢复写 Redis 失败 task=%s: %r", task_id, e)
            continue
        await _log_repo.mark_stale_failed(task_id, message)
        recovered += 1
    if recovered:
        logger.warning("重启恢复：%d 个未完成任务已置 failed", recovered)
    return recovered
