#!/usr/bin/env python3
"""step6 修正：shared/ 移出 contexts/ + page.py 归位

按用户决策：
1. contexts/shared/ → src/shared/（与 contexts/ 平级）
2. shared/application/port/page.py → shared/interface/page.py
3. interface 名字保留
4. 保持"骨架级"重构，不动业务逻辑

执行后：
- shared/ 不再是"context"，与 contexts/ 平级
- page.py 放在 DTO 集中的 interface/ 目录
"""
import os
import re
import shutil
from pathlib import Path

ROOT = Path("D:/codes/Attribution_Analysis/backend/src")

# ═══════════════════════════════════════════════════════════════
# 1. 移动：contexts/shared/* → shared/*
# ═══════════════════════════════════════════════════════════════
SHARED_MOVES = [
    # 旧 (在 contexts/shared/ 下)            → 新 (在 src/shared/ 下)
    ("contexts/shared/__init__.py",                    "shared/__init__.py"),
    ("contexts/shared/domain/__init__.py",             "shared/domain/__init__.py"),
    ("contexts/shared/domain/base.py",                 "shared/domain/base.py"),
    ("contexts/shared/domain/repository.py",           "shared/domain/repository.py"),
    ("contexts/shared/application/__init__.py",        "shared/application/__init__.py"),
    ("contexts/shared/application/port/__init__.py",   "shared/application/port/__init__.py"),
    ("contexts/shared/infrastructure/__init__.py",     "shared/infrastructure/__init__.py"),
    ("contexts/shared/infrastructure/persistence/__init__.py", "shared/infrastructure/persistence/__init__.py"),
    ("contexts/shared/infrastructure/persistence/connection.py",   "shared/infrastructure/persistence/connection.py"),
    ("contexts/shared/infrastructure/persistence/schema_init.py",  "shared/infrastructure/persistence/schema_init.py"),
    ("contexts/shared/infrastructure/persistence/orm_base.py",     "shared/infrastructure/persistence/orm_base.py"),
    ("contexts/shared/infrastructure/persistence/mixins.py",       "shared/infrastructure/persistence/mixins.py"),
    ("contexts/shared/infrastructure/persistence/models_registry.py", "shared/infrastructure/persistence/models_registry.py"),
    ("contexts/shared/infrastructure/cache/__init__.py",  "shared/infrastructure/cache/__init__.py"),
    ("contexts/shared/infrastructure/cache/redis_client.py", "shared/infrastructure/cache/redis_client.py"),
    ("contexts/shared/infrastructure/config/__init__.py", "shared/infrastructure/config/__init__.py"),
    ("contexts/shared/infrastructure/config/settings.py","shared/infrastructure/config/settings.py"),
    ("contexts/shared/infrastructure/config/di.py",      "shared/infrastructure/config/di.py"),
    ("contexts/shared/interface/__init__.py",   "shared/interface/__init__.py"),
    ("contexts/shared/interface/_response.py",  "shared/interface/_response.py"),
    ("contexts/shared/interface/router_compat.py", "shared/interface/router_compat.py"),
    # page.py 特殊处理：原 shared/application/port/page.py → shared/interface/page.py
    ("contexts/shared/application/port/page.py", "shared/interface/page.py"),
]

# ═══════════════════════════════════════════════════════════════
# 2. 清理：移完文件后，删 contexts/shared/ 空目录
# ═══════════════════════════════════════════════════════════════
CLEANUPS = [
    "contexts/shared",
    # 移走 page.py 后 application/port 目录变空 → 删除
    "shared/application/port",
    # application 目录变空 → 删除（如果只为了 page.py）
    "shared/application",
]

# ═══════════════════════════════════════════════════════════════
# 3. import 重写：
#    a. contexts.shared.X  → shared.X
#    b. contexts.shared.application.port.page → shared.interface.page
# ═══════════════════════════════════════════════════════════════
IMPORT_REWRITES = [
    # contexts.shared.*  → shared.*
    (r"^from contexts\.shared\.domain\.base\b",        "from shared.domain.base"),
    (r"^from contexts\.shared\.domain\.repository\b",  "from shared.domain.repository"),
    (r"^from contexts\.shared\.domain\b",              "from shared.domain"),
    (r"^from contexts\.shared\.application\.port\.page\b", "from shared.interface.page"),
    (r"^from contexts\.shared\.application\.port\b",   "from shared.application.port"),
    (r"^from contexts\.shared\.application\b",         "from shared.application"),
    (r"^from contexts\.shared\.infrastructure\.persistence\.connection\b",  "from shared.infrastructure.persistence.connection"),
    (r"^from contexts\.shared\.infrastructure\.persistence\.schema_init\b", "from shared.infrastructure.persistence.schema_init"),
    (r"^from contexts\.shared\.infrastructure\.persistence\.orm_base\b",    "from shared.infrastructure.persistence.orm_base"),
    (r"^from contexts\.shared\.infrastructure\.persistence\.mixins\b",      "from shared.infrastructure.persistence.mixins"),
    (r"^from contexts\.shared\.infrastructure\.persistence\.models_registry\b","from shared.infrastructure.persistence.models_registry"),
    (r"^from contexts\.shared\.infrastructure\.persistence\b", "from shared.infrastructure.persistence"),
    (r"^from contexts\.shared\.infrastructure\.cache\.redis_client\b", "from shared.infrastructure.cache.redis_client"),
    (r"^from contexts\.shared\.infrastructure\.cache\b", "from shared.infrastructure.cache"),
    (r"^from contexts\.shared\.infrastructure\.config\.settings\b", "from shared.infrastructure.config.settings"),
    (r"^from contexts\.shared\.infrastructure\.config\.di\b",      "from shared.infrastructure.config.di"),
    (r"^from contexts\.shared\.infrastructure\.config\b",         "from shared.infrastructure.config"),
    (r"^from contexts\.shared\.infrastructure\b",  "from shared.infrastructure"),
    (r"^from contexts\.shared\.interface\._response\b",  "from shared.interface._response"),
    (r"^from contexts\.shared\.interface\._response as R\b",  "from shared.interface import _response as R"),
    (r"^from contexts\.shared\.interface\.router_compat\b",  "from shared.interface.router_compat"),
    (r"^from contexts\.shared\.interface\b",  "from shared.interface"),
    (r"^from contexts\.shared\b",             "from shared"),
    # 注入 contexts.shared.infrastructure.persistence.models_registry
    (r"^import contexts\.shared\.infrastructure\.persistence\.models_registry",
        "import shared.infrastructure.persistence.models_registry"),
]


def do_moves():
    moved = 0
    for old, new in SHARED_MOVES:
        old_p = ROOT / old
        new_p = ROOT / new
        if old_p.exists():
            new_p.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(old_p), str(new_p))
            moved += 1
        elif new_p.exists():
            pass  # already done
        else:
            print(f"  WARN: {old} not found")
    print(f"  移动 {moved} 个文件（共 {len(SHARED_MOVES)}）")
    return moved


def do_rewrites():
    rewrite_count = 0
    for path in ROOT.rglob("*.py"):
        if "__pycache__" in str(path):
            continue
        text = path.read_text(encoding="utf-8")
        original = text
        for old_pattern, new_str in IMPORT_REWRITES:
            text = re.sub(old_pattern, new_str, text, flags=re.MULTILINE)
        if text != original:
            path.write_text(text, encoding="utf-8")
            rewrite_count += 1
    print(f"  改 import {rewrite_count} 个文件")
    return rewrite_count


def do_cleanup():
    for d in CLEANUPS:
        p = ROOT / d
        if p.exists() and p.is_dir():
            # 只删完全空的目录
            try:
                contents = list(p.iterdir())
                if not contents:
                    p.rmdir()
                    print(f"  删空目录: {d}")
                else:
                    print(f"  跳过非空目录: {d} (有 {len(contents)} 项)")
                    for x in contents:
                        print(f"    - {x.name}")
            except Exception as e:
                print(f"  跳过 {d}: {e}")


def verify():
    """最终校验"""
    import ast
    errors = []
    for path in ROOT.rglob("*.py"):
        if "__pycache__" in str(path):
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8"), str(path))
        except SyntaxError as e:
            errors.append((path, e.lineno, e.msg))
    print(f"  语法错误: {len(errors)}")
    for p, l, m in errors:
        print(f"    {p}:{l}  {m}")
    return len(errors)


def main():
    print("=" * 60)
    print("step6 修正：shared/ 移出 contexts/ + page.py 归位")
    print("=" * 60)
    print("\n[1] 移动 shared/ 文件")
    do_moves()
    print("\n[2] 改 import")
    do_rewrites()
    print("\n[3] 清理空目录")
    do_cleanup()
    print("\n[4] 最终校验")
    n = verify()
    if n == 0:
        print("\n[OK]")
    else:
        print(f"\n[FAIL] {n} 个语法错误")


if __name__ == "__main__":
    main()
