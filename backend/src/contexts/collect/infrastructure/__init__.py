"""infrastructure.collect — 基础设施层

- adapter/    外部 SDK / 调度适配
- fetcher/    外部数据抓取
- parser/     数据解析
- persistence/  ORM + 仓储实现
- sdk/         第三方 SDK 封装
- rate_limit.py  限流装饰器（限流原语 + 业务策略（合并 throttler））
- retry.py       重试装饰器
- cache/rate_limit.py  限流（原子原语 + collect 业务策略）
"""
