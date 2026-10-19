"""DDD 依赖方向检查

domain 层（含 entitys 与 exceptions）必须不 import：
  - contexts.collect.infrastructure.*
  - contexts.collect.application.*
  - fastapi / sqlalchemy / any infra 框架
  - any ORM 模型
"""
import ast
import os
import sys
from pathlib import Path

ROOT = Path(r"D:\codes\Attribution_Analysis\backend\src")

# 必须禁的 import 模式
FORBIDDEN = [
    "contexts.collect.infrastructure.",
    "contexts.collect.application.",
    "shared.infrastructure.persistence.",
    "fastapi",
    "sqlalchemy",
    "pydantic",  # 业务 BO 用了 pydantic，Protocol 可用 dataclass 或 typing
    "pymongo",
    "redis",
]

domain_root = ROOT / "contexts" / "collect" / "domain"
errors: list[str] = []


def check_one(path: Path) -> None:
    src = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src, filename=str(path))
    except SyntaxError as e:
        errors.append(f"[SYNTAX] {path.relative_to(ROOT)}: {e}")
        return

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for bad in FORBIDDEN:
                    if alias.name.startswith(bad):
                        errors.append(
                            f"[FORBIDDEN IMPORT] {path.relative_to(ROOT)}: {alias.name}"
                        )
        elif isinstance(node, ast.ImportFrom):
            frm = node.module or ""
            for bad in FORBIDDEN:
                if frm.startswith(bad):
                    errors.append(
                        f"[FORBIDDEN FROM] {path.relative_to(ROOT)}: from {frm} import ..."
                    )


# 遍历 domain 下所有 .py
for p in domain_root.rglob("*.py"):
    check_one(p)

# 报告
print("=" * 60)
print("DDD 依赖方向检查（domain 层）")
print("=" * 60)
if errors:
    print(f"❌ 发现 {len(errors)} 个违规：")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)
else:
    py_count = sum(1 for _ in domain_root.rglob("*.py"))
    print(f"✅ domain 层 {py_count} 个 .py 全部干净")
    sys.exit(0)
