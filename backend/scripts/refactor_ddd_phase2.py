"""DDD 重构 Phase 2:
1. 重写所有 src/*.py + tests/*.py 文件中的 import 路径
2. 删除旧 domain/<agg>/、application/dto/、application/exceptions.py、application/signals.py
3. 重建空的 application/ barrel
"""
from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

ROOT = Path(r"d:\codes\Attribution_Analysis\backend\src")
TESTS_ROOT = Path(r"d:\codes\Attribution_Analysis\backend\tests")

AGGREGATES = [
    "kline", "stock_info", "stock_pool", "fin_report", "fin_daily_basic",
    "cap_margin", "cap_moneyflow", "cap_margin_detail", "cap_top_list",
    "cap_top_inst", "cap_block_trade", "cap_holder_num",
    "fin_top10_holders", "fin_top10_float", "base_adj_factor", "base_dividend",
    "base_suspend", "base_name_change", "mkt_calendar", "mkt_market_daily",
    "mkt_sector_daily", "mkt_index_member", "concept",
]

EXC_TO_MODULE = {
    "KlineNotFoundError": "domain.entitys.kline.entity",
    "KlineDataError": "domain.entitys.kline.entity",
    "CollectionError": "domain.entitys.kline.entity",
    "StockNotFoundError": "domain.entitys.stock_info.entity",
    "PoolNotFoundError": "domain.entitys.stock_pool.entity",
    "PoolOperationNotFoundError": "domain.entitys.stock_pool.entity",
    "CannotDeleteDefaultPoolError": "domain.entitys.stock_pool.entity",
    "DuplicatePoolMemberError": "domain.entitys.stock_pool.entity",
    "PoolMemberNotFoundError": "domain.entitys.stock_pool.entity",
    "PoolOperationConflictError": "domain.entitys.stock_pool.entity",
    "ApplicationError": "domain.entitys.kline.entity",
}


def remap_import(line: str) -> str:
    if "from domain." not in line and "from application." not in line:
        return line
    # domain.<agg>.<sub> → domain.entitys.<agg>.<sub>
    for agg in AGGREGATES:
        line = re.sub(rf"from domain\.{agg}\.", f"from domain.entitys.{agg}.", line)
    line = re.sub(r"from domain\.panel\.", "from domain.entitys.panel.", line)

    # application/dto/<file> → route/dto/<request|response>/<file>
    line = re.sub(r"from application\.dto\.page", "from route.dto.page", line)
    line = re.sub(r"from application\.dto\.pool_operation", "from route.dto.request.pool_operation", line)
    line = re.sub(r"from application\.dto\.pool", "from route.dto.response.pool", line)
    line = re.sub(r"from application\.dto\.panel", "from route.dto.response.panel", line)
    line = re.sub(r"from application\.dto\.stock", "from route.dto.request.stock", line)
    line = re.sub(r"from application\.dto\.kline", "from route.dto.request.kline", line)
    line = re.sub(r"from application\.dto\.stock_analysis", "from route.dto.response.stock_analysis", line)
    line = re.sub(r"from application\.dto\.concept", "from route.dto.response.concept", line)

    # application.exceptions → 拆分
    line = re.sub(r"from application\.exceptions import\s*\(\s*([^)]+)\s*\)", _remap_exc_block, line)
    line = re.sub(r"from application\.exceptions import\s+(\w+)", _remap_exc_single, line)

    # application.signals → domain.entitys.kline.service.signal_detector
    line = re.sub(r"from application\.signals import", "from domain.entitys.kline.service.signal_detector import", line)

    return line


def _remap_exc_block(m: re.Match) -> str:
    names = [n.strip() for n in m.group(1).split(",") if n.strip()]
    return _emit_exc_imports(names)


def _remap_exc_single(m: re.Match) -> str:
    return _emit_exc_imports([m.group(1).strip()])


def _emit_exc_imports(names: list[str]) -> str:
    grouped: dict[str, list[str]] = {}
    for n in names:
        mod = EXC_TO_MODULE.get(n)
        if not mod:
            grouped.setdefault("application.exceptions", []).append(n)
        else:
            grouped.setdefault(mod, []).append(n)
    if len(grouped) == 1 and "application.exceptions" not in grouped:
        mod, items = next(iter(grouped.items()))
        return f"from {mod} import {', '.join(items)}"
    return "\n".join(f"from {mod} import {', '.join(items)}" for mod, items in grouped.items())


def rewrite_file(path: Path) -> bool:
    """重写单个 .py 文件的 import；返回是否改动"""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return False
    new_lines = [remap_import(ln) for ln in text.splitlines()]
    new_text = "\n".join(new_lines) + "\n"
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        return True
    return False


def rewrite_tree(root: Path) -> int:
    cnt = 0
    for p in root.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        if rewrite_file(p):
            cnt += 1
    return cnt


def main() -> None:
    print("Phase 2: rewriting imports ...")
    n1 = rewrite_tree(ROOT)
    print("  - %d files in src/" % n1)

    if TESTS_ROOT.exists():
        n2 = rewrite_tree(TESTS_ROOT)
        print("  - %d files in tests/" % n2)

    # 删除旧 domain/<agg>/（除 entitys/, panel/, base.py, __init__.py）
    print("Phase 3: removing legacy directories ...")
    legacy_root = ROOT / "domain"
    keep = {"entitys", "panel", "__init__.py", "base.py", "__pycache__"}
    for entry in legacy_root.iterdir():
        if entry.name in keep:
            continue
        if entry.is_dir():
            shutil.rmtree(entry, ignore_errors=True)
            print("  - removed dir: domain/%s" % entry.name)

    # 删除 application/dto/
    dto_dir = ROOT / "application" / "dto"
    if dto_dir.exists():
        shutil.rmtree(dto_dir, ignore_errors=True)
        print("  - removed: application/dto/")

    # 删除 application/exceptions.py
    exc_file = ROOT / "application" / "exceptions.py"
    if exc_file.exists():
        exc_file.unlink()
        print("  - removed: application/exceptions.py")

    # 删除 application/signals.py
    sig_file = ROOT / "application" / "signals.py"
    if sig_file.exists():
        sig_file.unlink()
        print("  - removed: application/signals.py")

    # 删除 entitys/<agg>/_schemas_temp.py（schemas 已迁走）
    for agg in AGGREGATES + ["panel"]:
        tp = ROOT / "domain" / "entitys" / agg / "_schemas_temp.py"
        if tp.exists():
            tp.unlink()

    print("\n[OK] phase 2 done.")


if __name__ == "__main__":
    main()
