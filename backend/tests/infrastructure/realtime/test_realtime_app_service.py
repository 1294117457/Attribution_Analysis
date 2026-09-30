"""实时接口执行入口单元测试（内存假 Redis）

  · 缓存命中不调 fetch
  · 并发同 key 只调一次 fetch（单飞）
  · 失败走降级、stale=true、不缓存；无降级抛错
  · ttl_for 按交易时段计算
  · stock_minute_kline 参数校验
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime

import pytest

from application.service import realtime_app_service as svc_mod
from application.service.realtime_app_service import RealtimeAppService, RealtimeQueryError
from infrastructure.adapter.realtime import registry as rt_registry
from infrastructure.adapter.realtime.base import MARKET_TZ, BaseRealtimeQuery, ttl_for
from infrastructure.adapter.realtime.stock_minute_kline import StockMinuteKlineQuery


class FakeRedis:
    def __init__(self):
        self.kv: dict[str, tuple[str, float | None]] = {}
        self.hashes: dict[str, dict] = {}

    def _alive(self, key):
        v = self.kv.get(key)
        if v is None:
            return None
        if v[1] is not None and v[1] < time.monotonic():
            del self.kv[key]
            return None
        return v[0]

    async def ping(self):
        return True

    async def get(self, key):
        return self._alive(key)

    async def set(self, key, value, nx=False, ex=None):
        if nx and self._alive(key) is not None:
            return None
        self.kv[key] = (value, time.monotonic() + ex if ex else None)
        return True

    async def delete(self, key):
        self.kv.pop(key, None)

    async def hgetall(self, key):
        return dict(self.hashes.get(key, {}))

    def pipeline(self):
        return _Pipe(self)


class _Pipe:
    def __init__(self, r: FakeRedis):
        self.r, self.ops = r, []

    def hincrby(self, key, field, n):
        self.ops.append(lambda: self._inc(key, field, n))

    def hincrbyfloat(self, key, field, n):
        self.ops.append(lambda: self._inc(key, field, n))

    def hset(self, key, mapping):
        self.ops.append(lambda: self.r.hashes.setdefault(key, {}).update(mapping))

    def expire(self, key, seconds):
        pass

    def _inc(self, key, field, n):
        h = self.r.hashes.setdefault(key, {})
        total = float(h.get(field, 0)) + n
        h[field] = str(int(total)) if isinstance(n, int) else str(total)

    async def execute(self):
        for op in self.ops:
            op()


class DemoQuery(BaseRealtimeQuery):
    name = "demo"
    label = "演示"
    source = "demo"

    def __init__(self, fail=False, fallback_value=None, delay=0.0):
        self.calls = 0
        self.fail = fail
        self.fallback_value = fallback_value
        self.delay = delay

    def cache_key(self, params):
        return params["k"]

    async def fetch(self, params):
        self.calls += 1
        await asyncio.sleep(self.delay)
        if self.fail:
            raise RuntimeError("source down")
        return {"k": params["k"], "n": self.calls}

    async def fallback(self, params):
        return self.fallback_value


@pytest.fixture
def redis(monkeypatch):
    r = FakeRedis()

    async def _get():
        return r

    monkeypatch.setattr(svc_mod, "get_redis", _get)
    return r


def _setup(monkeypatch, query):
    monkeypatch.setattr(rt_registry, "_registry", None)
    rt_registry.setup_realtime_registry([query])
    return RealtimeAppService()


async def test_cache_hit_skips_fetch(monkeypatch, redis):
    q = DemoQuery()
    svc = _setup(monkeypatch, q)
    first = await svc.query("demo", {"k": "a"})
    second = await svc.query("demo", {"k": "a"})
    assert q.calls == 1
    assert first.cached is False and second.cached is True
    assert second.data == first.data


async def test_single_flight(monkeypatch, redis):
    q = DemoQuery(delay=0.2)
    svc = _setup(monkeypatch, q)
    results = await asyncio.gather(*(svc.query("demo", {"k": "a"}) for _ in range(10)))
    assert q.calls == 1
    assert all(r.data == results[0].data for r in results)


async def test_fallback_is_stale_and_not_cached(monkeypatch, redis):
    q = DemoQuery(fail=True, fallback_value={"price": 1.0})
    svc = _setup(monkeypatch, q)
    res = await svc.query("demo", {"k": "a"})
    assert res.stale is True and res.data == {"price": 1.0}
    assert await redis.get("rt:demo:a") is None
    await svc.query("demo", {"k": "a"})
    assert q.calls == 2


async def test_failure_without_fallback_raises(monkeypatch, redis):
    svc = _setup(monkeypatch, DemoQuery(fail=True))
    with pytest.raises(RealtimeQueryError):
        await svc.query("demo", {"k": "a"})
    stats = await svc.stats("demo")
    assert stats[0]["errors"] == 1 and stats[0]["calls"] == 1


async def test_query_many_isolates_errors(monkeypatch, redis):
    svc = _setup(monkeypatch, DemoQuery())
    results = await svc.query_many("demo", [{"k": "a"}, {}])
    assert results[0].data["k"] == "a"
    assert results[1].data is None and results[1].error


def _at(y, m, d, hh, mm):
    return datetime(y, m, d, hh, mm, tzinfo=MARKET_TZ)


@pytest.mark.parametrize(
    "now, expected",
    [
        (_at(2026, 9, 30, 10, 0), 15),                   # 周三上午盘中
        (_at(2026, 9, 30, 14, 59), 15),                  # 下午盘中
        (_at(2026, 9, 30, 12, 0), 3600),                 # 午休到 13:00
        (_at(2026, 9, 30, 9, 0), 25 * 60),               # 盘前到 09:25
        (_at(2026, 9, 30, 15, 0), (18 * 60 + 25) * 60),  # 收盘到次日 09:25
        (_at(2026, 10, 2, 16, 0), (65 * 60 + 25) * 60),  # 周五收盘到周一 09:25
    ],
)
def test_ttl_for(now, expected):
    assert ttl_for(15, now) == expected


class TestStockMinuteKlineParams:
    q = StockMinuteKlineQuery()

    def test_days_default_and_key(self):
        p = self.q.normalize({"symbol": "600519", "interval": "1min"})
        assert p == {"symbol": "600519", "interval": "1min", "days": 1}
        assert self.q.cache_key(p) == "600519:1min:1"

    def test_1min_only_today(self):
        with pytest.raises(ValueError):
            self.q.normalize({"symbol": "600519", "interval": "1min", "days": 3})

    def test_other_interval_max_5_days(self):
        assert self.q.normalize({"symbol": "000001", "interval": "5min", "days": 5})["days"] == 5
        with pytest.raises(ValueError):
            self.q.normalize({"symbol": "000001", "interval": "5min", "days": 10})

    def test_legacy_count(self):
        p = self.q.normalize({"symbol": "600519", "interval": "5min", "count": 200})
        assert self.q.cache_key(p) == "600519:5min:c200"

    @pytest.mark.parametrize("symbol", ["830799", "430047", "920001"])
    def test_bse_rejected(self, symbol):
        with pytest.raises(ValueError, match="北交所"):
            self.q.normalize({"symbol": symbol})
