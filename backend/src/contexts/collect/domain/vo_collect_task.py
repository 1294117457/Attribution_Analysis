"""采集任务值对象：单次执行的统计结果（纯规则，零外部依赖）

配套设计文档：docs/backend-docs/dev/step5/03collect优化/01-领域规则下沉.md
"""

from __future__ import annotations

from dataclasses import dataclass

from contexts.shared.domain.base import ValueObject


@dataclass(frozen=True)
class TaskOutcome(ValueObject):
    """一次采集任务执行的统计结果

    规则：零成功且有失败 → failed；其余（含部分失败）→ success。
    "部分失败也算 success"是既有语义（前端历史列表依赖），保持不变。
    """

    success: int
    fail: int
    skip: int = 0

    @property
    def status(self) -> str:
        return "failed" if self.success == 0 and self.fail > 0 else "success"

    @property
    def all_failed(self) -> bool:
        return self.success == 0 and self.fail > 0

    def _get_values(self) -> tuple:
        return (self.success, self.fail, self.skip)


__all__ = ["TaskOutcome"]
