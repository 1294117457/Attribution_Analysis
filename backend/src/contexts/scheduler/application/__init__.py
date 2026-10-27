"""scheduler application - 调度相关 service 占位

本期（拆分）暂不写任何 service。
后续接入时按 collect runner 的语义补：
  - ScheduleAppService        (CRUD / 启停 / 改 / 删)
  - ScheduleRunner            (轮询 schedule 表 + 触发 service)

运行日志不写本 context 的 service —— 统一走 `shared.infrastructure.log_util`。
"""
