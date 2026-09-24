"""概念领域异常

配套设计文档：
  docs/dev/06gainian/01-domain-design.md §6
"""

from __future__ import annotations


class ConceptNotFoundError(Exception):
    """指定概念不存在（按 id / name 查不到）"""

    message: str

    def __init__(self, *, id: int | None = None, name: str | None = None):
        if id is not None:
            self.message = f"概念 id={id} 不存在"
        elif name is not None:
            self.message = f"概念 name={name!r} 不存在"
        else:
            self.message = "概念不存在"
        super().__init__(self.message)
