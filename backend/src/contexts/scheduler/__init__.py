"""scheduler context - 调度模块（拆分骨架）

本期（拆分）只包含：
  - domain.entitys.schedule  (Schedule 聚合根 + 仓储协议 + VO)
  - domain.entitys.run_log   (RunLog 聚合根 + 仓储协议 + VO)
  - application.port         (ApschedulerPort 协议占位)
  - infrastructure.persistence  (ORM + SqlScheduleRepository / SqlRunLogRepository)

⚠️ 本期不实现：
  - APScheduler 适配器
  - 调度 runner
  - 调度相关 HTTP 路由
  - 调度 CRUD HTTP API
  - 调度相关 DTO

⚠️ DB 表名本期保留 `collect_schedule` / `collect_run_log`，**不迁移**。
后续可加：
  - ALTER TABLE collect_schedule RENAME TO schedule;
  - ALTER TABLE collect_run_log  RENAME TO collect_run_log_legacy;   -- 视情况
"""
