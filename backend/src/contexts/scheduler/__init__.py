"""scheduler context - 调度模块（拆分骨架）

本期（拆分）只包含：
  - domain.entitys.schedule  (Schedule 聚合根 + 仓储协议 + VO)
  - application.port         (ApschedulerPort 协议占位)
  - infrastructure.persistence  (ORM + SqlScheduleRepository)

⚠️ 本期不实现：
    - APScheduler 适配器
  - 调度 runner
  - 调度相关 HTTP 路由
  - 调度 CRUD HTTP API
  - 调度相关 DTO

⚠️ 运行日志统一走 `shared.infrastructure.log_util`（表 collect_logs），
  本 context 不再维护第二套 run_log 表 —— 避免两张语义重叠的日志表。
  将来接入 APScheduler 时，直接在调度触发侧调用 log_util 即可。
"""
