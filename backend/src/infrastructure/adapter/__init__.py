"""基础设施适配器（ACL 防腐层）

- data/        数据源 Adapter + DataGateway（取数统一入口，见 infrastructure.adapter.data）
- collect/     采集任务（取 + 入库，task_type → BaseCollectTask）
- scheduler/   SchedulerPort 的 APScheduler 实现
- background/  股票池操作的后台任务派发
- cache/       Redis 客户端
"""
