"""Redis 异步客户端

远端 Redis（8.148.204.54）会自动回收空闲连接，需要：
- socket_keepalive=True           TCP keepalive
- health_check_interval=30        每 30s 发 PING,失败自动重建
- retry_on_timeout=True           超时重试
- socket_timeout=5                防止长时间阻塞
- single client 全局复用          复用连接池

注意：本模块历史上曾因 `get_collect_manage_service()` sync 工厂 + 未 await 的
coroutine 造成每次调用都新建 Redis 客户端 → 服务端连接数爆炸
（症状："Too many connections" warning 每秒几十条）。
修复方案：
  1. di.py 改为 `_LazyRedisPort` 延迟初始化（事件循环中真正 await）
  2. 本模块加 max_connections 上限，防止连接池被滥用
"""
import redis.asyncio as aioredis
from redis.exceptions import ConnectionError as RedisConnectionError
import asyncio
import time
import logging
from infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None
_init_lock: asyncio.Lock | None = None

# 健康状态缓存：避免 Redis 真正不可用时每个请求都 ping 一次
_unhealthy_until: float = 0.0
_UNHEALTHY_CACHE_SEC = 30.0  # 失败后 30s 内不再 ping

# 连接池上限（远端 Redis 服务端 maxclients 通常 10000，但共享实例要克制）
MAX_CONNECTIONS = 20


def _build_client() -> aioredis.Redis:
    """按当前配置构建一个新的 Redis 客户端（含连接池）"""
    settings = get_settings()
    return aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        # 连接保活：避免远端 Redis 主动断开空闲连接导致 10054
        socket_keepalive=True,
        socket_timeout=5,
        socket_connect_timeout=5,
        # 健康检查：30s 一次 PING,失败自动重建
        health_check_interval=30,
        # 重试：超时/连接错误自动重试 1 次
        retry_on_timeout=True,
        retry_on_error=[ConnectionError, TimeoutError],
        # 连接池上限：防止被滥用拖垮 Redis 服务端
        max_connections=MAX_CONNECTIONS,
    )


async def get_redis() -> aioredis.Redis:
    """获取全局 Redis 单例（事件循环内 lazy 初始化）"""
    global _redis, _init_lock
    if _redis is None:
        if _init_lock is None:
            _init_lock = asyncio.Lock()
        async with _init_lock:
            if _redis is None:  # double-check
                _redis = _build_client()
                logger.info("Redis 客户端初始化完成 (max_connections=%d)", MAX_CONNECTIONS)
    return _redis


async def reset_redis_client(reason: str = "") -> None:
    """丢弃并重建全局 Redis 客户端（连接池耗尽 / 连接损坏时自愈用）

    场景：远端 Redis 返回 `Too many connections` 时，说明当前连接池里的
    socket 全部被服务端拒绝/悬挂。本地池子再重试也没用，必须换一个干净池子。
    """
    global _redis
    old = _redis
    _redis = None
    if old is not None:
        try:
            await old.aclose()
        except Exception:
            pass
    _redis = _build_client()
    logger.warning("Redis 客户端已重建（原因: %s）", reason or "unknown")


async def try_get_redis() -> aioredis.Redis | None:
    """取 Redis；失败时缓存"不健康"状态 30s,避免雪崩

    用法（实时接口降级场景）：
        redis = await try_get_redis()
        if redis is None:
            # 走直连数据源分支，不打 warning 刷屏
            ...

    `Too many connections` 这类"池子脏了"的错误会触发一次客户端重建后重试。
    """
    global _unhealthy_until
    if time.time() < _unhealthy_until:
        return None
    try:
        redis = await get_redis()
        await redis.ping()
        return redis
    except Exception as e:
        # 连接池耗尽 / 连接损坏 → 重建客户端再试一次
        if _is_pool_exhausted(e):
            logger.warning("Redis 连接池耗尽，尝试重建客户端: %s", e)
            try:
                await reset_redis_client(str(e))
                redis = await get_redis()
                await redis.ping()
                _unhealthy_until = 0.0
                return redis
            except Exception as e2:
                e = e2  # 重建后仍失败 → 走下面的缓存分支

        _unhealthy_until = time.time() + _UNHEALTHY_CACHE_SEC
        logger.warning(
            "Redis 不可用，缓存 30s 跳过 ping: %s (cache_until=%s)",
            e, time.strftime("%H:%M:%S", time.localtime(_unhealthy_until)),
        )
        return None


def _is_pool_exhausted(exc: Exception) -> bool:
    """判断异常是否是"连接池耗尽 / 服务端拒绝连接"类错误"""
    msg = str(exc).lower()
    markers = (
        "too many connections",
        "maxclients",
        "connection pool",
        "connectionpool",
        "exhausted",
        "no connection available",
    )
    return any(m in msg for m in markers)


async def reset_unhealthy_cache() -> None:
    """手动清除不健康缓存（lifespan / 测试场景用）"""
    global _unhealthy_until
    _unhealthy_until = 0.0
