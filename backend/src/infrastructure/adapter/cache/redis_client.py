"""Redis 异步客户端

远端 Redis（8.148.204.54）会自动回收空闲连接，需要：
- socket_keepalive=True           TCP keepalive
- health_check_interval=30        每 30s 发 PING,失败自动重建
- retry_on_timeout=True           超时重试
- socket_timeout=5                防止长时间阻塞
- single client 全局复用          复用连接池
"""
import redis.asyncio as aioredis
from infrastructure.config.settings import get_settings

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = aioredis.from_url(
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
        )
    return _redis
