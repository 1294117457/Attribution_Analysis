"""极简模板渲染（P0 设计）

仅支持 {{var}} 和 {{var.attr}} 替换，**不支持 filter（如 {{x|default(7)}}）**。
默认值在 UnitResolver 阶段填，模板只做替换。

为什么自写：
  - 不引入 jinja2 依赖
  - 字典/列表/字符串递归渲染都处理
  - 找不到变量时返回空字符串，不抛错
"""

from __future__ import annotations

import re
from typing import Any

_VAR_RE = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")


def render(template: Any, ctx: dict) -> Any:
    """递归渲染：dict / list / tuple / str 都处理；str 里的 {{var}} 替换为 str

    行为：模板中的 {{var}} 一律替换为 str(ctx[var])。
    如果调用方希望保留 int/float 类型（如 days=30），
    应在 PipelineRunner 渲染后做类型转换（用 inspect.signature 自动推断）。
    """
    if isinstance(template, str):
        return _VAR_RE.sub(lambda m: _to_str(_lookup(ctx, m.group(1).strip())), template)
    if isinstance(template, dict):
        return {k: render(v, ctx) for k, v in template.items()}
    if isinstance(template, list):
        return [render(x, ctx) for x in template]
    if isinstance(template, tuple):
        return tuple(render(x, ctx) for x in template)
    return template


def _to_str(val: Any) -> str:
    """模板嵌入用：任何值转字符串"""
    if val is None:
        return ""
    return str(val)


def _lookup(ctx: dict, path: str) -> Any:
    """支持 a.b.c 路径查找；找不到返回 ''

    Args:
        ctx: 上下文 dict
        path: 变量路径，如 "symbol" / "params.days" / "config.name"
    """
    cur: Any = ctx
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part, "")
            if cur == "":
                return ""
        elif hasattr(cur, part):
            cur = getattr(cur, part, "")
            if cur == "":
                return ""
        else:
            return ""
    return cur if cur is not None else ""


__all__ = ["render"]
