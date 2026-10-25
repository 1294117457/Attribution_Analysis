"""infrastructure.collect — 基础设施层

- adapter/    外部 SDK / 调度适配
- fetcher/    外部数据抓取
- parser/     数据解析
- persistence/  ORM + 仓储实现
- sdk/         第三方 SDK 封装
- connect/      外部 SDK 连接（tushare / adata / pytdx）
    限流下沉在这一层：每个 client 的唯一出口调用 cache/rate_limit.acquire()
- cache/rate_limit.py  限流（通用 Redis 固定窗口原语，阈值由调用方传入）
- retry.py       重试装饰器
"""