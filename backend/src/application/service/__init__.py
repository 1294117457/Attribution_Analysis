"""Application 层：业务用例编排（按业务模块组织）

业务模块（与前端 views/ 下的子目录 1:1 对齐）：
- AuthService           认证授权（auth/）
- StockInfoService      股票信息（stock-info/）+ 面板 + K 线 + 归因分析
- StockPoolService      操作池（stock-pool/）+ 池操作派发
- CollectManageService  采集管理（collect-manage/）+ 任务调度
- ConceptService        概念基础查询（被 stock-info / market 复用）
- ConceptBoardService   概念大盘（concept-board/）+ 概念日 K + 实时

设计原则：
- 不持有 AsyncSession：所有依赖通过构造注入（DDD.md §4）
- 不 import `infrastructure.*`：基础设施适配通过 DI 注入
- 旧 application.service.<x>_app_service 已删除，本目录为唯一入口
"""

from application.service.auth_service import AuthService
from application.service.collect_manage_service import (
    CollectManageService,
    TaskConflict,
    UnknownTaskType,
    cancel_background,
    task_to_dict,
)
from application.service.concept_board_service import ConceptBoardService
from application.service.concept_service import ConceptService
from application.service.stock_info_service import StockInfoService
from application.service.stock_pool_service import StockPoolService

__all__ = [
    "AuthService",
    "CollectManageService",
    "ConceptBoardService",
    "ConceptService",
    "StockInfoService",
    "StockPoolService",
    # 采集相关辅助符号
    "TaskConflict",
    "UnknownTaskType",
    "cancel_background",
    "task_to_dict",
]
