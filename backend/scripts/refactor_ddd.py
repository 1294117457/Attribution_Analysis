"""DDD 重构：批量迁移 domain/* → domain/entitys/* + application/dto → route/dto

执行：python d:\codes\Attribution_Analysis\backend\scripts\refactor_ddd.py
"""
from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

ROOT = Path(r"d:\codes\Attribution_Analysis\backend\src")

# ───────────────────────────────────────────────────────────────────────────
# 24 个聚合根
# ───────────────────────────────────────────────────────────────────────────
AGGREGATES = [
    "kline",
    "stock_info",
    "stock_pool",
    "fin_report",
    "fin_daily_basic",
    "cap_margin",
    "cap_moneyflow",
    "cap_margin_detail",
    "cap_top_list",
    "cap_top_inst",
    "cap_block_trade",
    "cap_holder_num",
    "fin_top10_holders",
    "fin_top10_float",
    "base_adj_factor",
    "base_dividend",
    "base_suspend",
    "base_name_change",
    "mkt_calendar",
    "mkt_market_daily",
    "mkt_sector_daily",
    "mkt_index_member",
    "concept",
]

# domain/panel 是跨聚合组合上下文，独立处理
# ───────────────────────────────────────────────────────────────────────────
# import 映射：旧路径 → 新路径
# ───────────────────────────────────────────────────────────────────────────
def remap_import(line: str) -> str:
    """重写 import 路径（domain.*, application.dto.*, application.exceptions）"""
    if "from domain." not in line and "from application." not in line:
        return line

    # domain.<agg>.<sub>  →  domain.entitys.<agg>.<sub>
    for agg in AGGREGATES:
        line = re.sub(
            rf"from domain\.{agg}\.",
            f"from domain.entitys.{agg}.",
            line,
        )
    # domain.panel.* → domain.entitys.panel.*
    line = re.sub(r"from domain\.panel\.", "from domain.entitys.panel.", line)

    # application/dto/*  →  route/dto/*
    # 根据 dto 模块名路由到 request/ response/ page
    line = re.sub(
        r"from application\.dto\.page",
        "from route.dto.page",
        line,
    )
    line = re.sub(
        r"from application\.dto\.pool_operation",
        "from route.dto.request.pool_operation",
        line,
    )
    line = re.sub(
        r"from application\.dto\.pool",
        "from route.dto.response.pool",
        line,
    )
    # panel dto → response
    line = re.sub(
        r"from application\.dto\.panel",
        "from route.dto.response.panel",
        line,
    )
    line = re.sub(
        r"from application\.dto\.stock",
        "from route.dto.request.stock",
        line,
    )
    line = re.sub(
        r"from application\.dto\.kline",
        "from route.dto.request.kline",
        line,
    )
    line = re.sub(
        r"from application\.dto\.stock_analysis",
        "from route.dto.response.stock_analysis",
        line,
    )
    line = re.sub(
        r"from application\.dto\.concept",
        "from route.dto.response.concept",
        line,
    )

    # application.exceptions → 拆分到各聚合根 entity
    # KlineNotFoundError, KlineDataError, CollectionError → domain.entitys.kline.entity
    # StockNotFoundError → domain.entitys.stock_info.entity
    # PoolNotFoundError, PoolOperationNotFoundError, CannotDeleteDefaultPoolError,
    # DuplicatePoolMemberError, PoolMemberNotFoundError, PoolOperationConflictError
    # → domain.entitys.stock_pool.entity
    # ApplicationError, KlineNotFoundError ... 使用具体来源
    line = re.sub(
        r"from application\.exceptions import\s*\(\s*([^)]+)\s*\)",
        _remap_exceptions_block,
        line,
    )
    line = re.sub(
        r"from application\.exceptions import\s+(\w+)",
        _remap_exceptions_single,
        line,
    )

    # application.signals → domain.entitys.kline.service.signal_detector
    line = re.sub(
        r"from application\.signals import",
        "from domain.entitys.kline.service.signal_detector import",
        line,
    )

    return line


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


def _remap_exceptions_block(match: re.Match) -> str:
    """from application.exceptions import (A, B, C) → 按归属拆分"""
    body = match.group(1)
    names = [n.strip() for n in body.split(",") if n.strip()]
    return _emit_imports(names)


def _remap_exceptions_single(match: re.Match) -> str:
    name = match.group(1).strip()
    return _emit_imports([name])


def _emit_imports(names: list[str]) -> str:
    """按目标模块分组，输出多行 from import"""
    grouped: dict[str, list[str]] = {}
    for n in names:
        mod = EXC_TO_MODULE.get(n)
        if not mod:
            # 未知异常：保留 application.exceptions 作为兜底
            grouped.setdefault("application.exceptions", []).append(n)
        else:
            grouped.setdefault(mod, []).append(n)
    if len(grouped) == 1 and "application.exceptions" not in grouped:
        mod, items = next(iter(grouped.items()))
        return f"from {mod} import {', '.join(items)}"
    lines = []
    for mod, items in grouped.items():
        lines.append(f"from {mod} import {', '.join(items)}")
    return "\n".join(lines)


# ───────────────────────────────────────────────────────────────────────────
# 文件内容改写（合并 DTO 拆分、events、exceptions 到 entity/vo）
# ───────────────────────────────────────────────────────────────────────────
def merge_domain_aggregate(agg: str) -> None:
    """domain/<agg>/{entity,repository,value_objects,schemas,events}.py
       →  domain/entitys/<agg>/{entity,repository,vo}.py
    """
    src_dir = ROOT / "domain" / agg
    dst_dir = ROOT / "domain" / "entitys" / agg
    dst_dir.mkdir(parents=True, exist_ok=True)

    # 1. entity.py：合并 events + exceptions（如果有）
    entity_src = src_dir / "entity.py"
    entity_dst = dst_dir / "entity.py"
    entity_text = entity_src.read_text(encoding="utf-8") if entity_src.exists() else ""
    # events.py：领域事件合并到 entity.py（保留原样追加）
    events_src = src_dir / "events.py"
    if events_src.exists():
        events_text = events_src.read_text(encoding="utf-8")
        entity_text += "\n\n# ── 领域事件 ──\n\n" + events_text
    # exceptions.py：合并到 entity.py（仅适用于 concept）
    exc_src = src_dir / "exceptions.py"
    if exc_src.exists():
        exc_text = exc_src.read_text(encoding="utf-8")
        entity_text += "\n\n# ── 领域异常 ──\n\n" + exc_text
    entity_dst.write_text(_rewrite(entity_text), encoding="utf-8")

    # 2. repository.py：保留
    for fname in ("repository.py",):
        src = src_dir / fname
        if src.exists():
            (dst_dir / fname).write_text(_rewrite(src.read_text(encoding="utf-8")), encoding="utf-8")

    # 3. value_objects.py → vo.py
    vo_src = src_dir / "value_objects.py"
    vo_dst = dst_dir / "vo.py"
    if vo_src.exists():
        vo_dst.write_text(_rewrite(vo_src.read_text(encoding="utf-8")), encoding="utf-8")

    # 4. schemas.py 内容**保留**（这是 DTO），后续单独搬到 route/dto
    schemas_src = src_dir / "schemas.py"
    if schemas_src.exists():
        # 暂存到 entitys/<agg>/_schemas_temp.py，等会儿搬到 route/dto
        (dst_dir / "_schemas_temp.py").write_text(
            _rewrite(schemas_src.read_text(encoding="utf-8")), encoding="utf-8"
        )

    # 5. service/ 子目录（如有）：合并到 entitys/<agg>/service/
    src_svc = src_dir / "service"
    if src_svc.exists() and src_svc.is_dir():
        dst_svc = dst_dir / "service"
        dst_svc.mkdir(exist_ok=True)
        for f in src_svc.iterdir():
            if f.is_file() and f.suffix == ".py":
                # 重命名：indicator_calculator → calculator（简洁）
                (dst_svc / f.name).write_text(
                    _rewrite(f.read_text(encoding="utf-8")), encoding="utf-8"
                )


def _rewrite(text: str) -> str:
    """重写文件内容中的 import"""
    out_lines = []
    for line in text.splitlines():
        out_lines.append(remap_import(line))
    return "\n".join(out_lines) + "\n"


# ───────────────────────────────────────────────────────────────────────────
# panel 上下文（独立处理）
# ───────────────────────────────────────────────────────────────────────────
def migrate_panel() -> None:
    src_dir = ROOT / "domain" / "panel"
    dst_dir = ROOT / "domain" / "entitys" / "panel"
    dst_dir.mkdir(parents=True, exist_ok=True)
    for fname in ("repository.py", "value_objects.py"):
        src = src_dir / fname
        if src.exists():
            target_name = fname.replace("value_objects.py", "vo.py")
            (dst_dir / target_name).write_text(
                _rewrite(src.read_text(encoding="utf-8")), encoding="utf-8"
            )
    # panel 无 entity、无 schemas、无 exceptions、无 service


# ───────────────────────────────────────────────────────────────────────────
# DTO 迁移：domain/<agg>/schemas.py → route/dto/
# ───────────────────────────────────────────────────────────────────────────
def migrate_dtos() -> None:
    """所有 schemas.py 重新分类到 request/ response/ 下"""
    entitys_dir = ROOT / "domain" / "entitys"

    # 1. 通用 page（应用层 page.py）
    page_src = ROOT / "application" / "dto" / "page.py"
    if page_src.exists():
        target = ROOT / "route" / "dto" / "page.py"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_rewrite(page_src.read_text(encoding="utf-8")), encoding="utf-8")

    # 2. application/dto/* → route/dto/*
    dto_src_dir = ROOT / "application" / "dto"
    dto_dst_dir = ROOT / "route" / "dto"
    dto_dst_dir.mkdir(parents=True, exist_ok=True)
    (dto_dst_dir / "request").mkdir(exist_ok=True)
    (dto_dst_dir / "response").mkdir(exist_ok=True)

    # 哪些是 request、哪些是 response
    request_files = {"kline.py", "stock.py", "pool_operation.py"}
    # 其他：pool.py, panel.py, stock_analysis.py, concept.py → response（按 VO 命名判断）

    for f in dto_src_dir.iterdir():
        if not f.is_file() or f.suffix != ".py" or f.name == "__init__.py" or f.name == "page.py":
            continue
        content = _rewrite(f.read_text(encoding="utf-8"))
        if f.name in request_files:
            (dto_dst_dir / "request" / f.name).write_text(content, encoding="utf-8")
        else:
            (dto_dst_dir / "response" / f.name).write_text(content, encoding="utf-8")

    # 3. domain/<agg>/schemas.py → route/dto/<request|response>/<agg>.py
    # 决策：schemas.py 里包含 *BO（input）是 request，包含 *VO（output）是 response。
    # 但很多 schemas.py 同时有 BO 和 VO，需要拆分。
    for agg in AGGREGATES:
        schemas_path = entitys_dir / agg / "_schemas_temp.py"
        if not schemas_path.exists():
            continue
        text = schemas_path.read_text(encoding="utf-8")
        request_lines = []
        response_lines = []
        other_lines = []
        # 简单规则：class *BO → request，class *VO → response
        cur_section = "other"
        for line in text.splitlines():
            m = re.match(r"^class\s+(\w+)\b", line)
            if m:
                name = m.group(1)
                if name.endswith("BO"):
                    cur_section = "request"
                elif name.endswith("VO") or "ValueObject" in name or "Stat" in name:
                    cur_section = "response"
                else:
                    cur_section = "response"  # 兜底
            if cur_section == "request":
                request_lines.append(line)
            elif cur_section == "response":
                response_lines.append(line)
            else:
                other_lines.append(line)

        # 写入 request
        if request_lines:
            req_target = dto_dst_dir / "request" / f"{agg}.py"
            header = "\"\"\"自动迁移自 domain/{}/schemas.py（BO 部分）\"\"\"\n\nfrom __future__ import annotations\n\n".format(agg)
            req_target.write_text(header + "\n".join(request_lines) + "\n", encoding="utf-8")
        # 写入 response
        if response_lines:
            resp_target = dto_dst_dir / "response" / f"{agg}.py"
            header = "\"\"\"自动迁移自 domain/{}/schemas.py（VO 部分）\"\"\"\n\nfrom __future__ import annotations\n\n".format(agg)
            resp_target.write_text(header + "\n".join(response_lines) + "\n", encoding="utf-8")


# ───────────────────────────────────────────────────────────────────────────
# signals 迁移
# ───────────────────────────────────────────────────────────────────────────
def migrate_signals() -> None:
    src = ROOT / "application" / "signals.py"
    if not src.exists():
        return
    target_dir = ROOT / "domain" / "entitys" / "kline" / "service"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "signal_detector.py"
    text = _rewrite(src.read_text(encoding="utf-8"))
    # 修正 import：from domain.entitys.kline.entity import Kline
    target.write_text(text, encoding="utf-8")


# ───────────────────────────────────────────────────────────────────────────
# 主流程
# ───────────────────────────────────────────────────────────────────────────
def main() -> None:
    print("Step 1: migrate 24 aggregates to domain/entitys/ ...")
    for agg in AGGREGATES:
        merge_domain_aggregate(agg)
        print("  - %s" % agg)

    print("Step 2: migrate panel ...")
    migrate_panel()

    print("Step 3: migrate application/dto/ -> route/dto/ ...")
    migrate_dtos()

    print("Step 4: migrate application/signals.py -> domain/entitys/kline/service/ ...")
    migrate_signals()

    print("\n[OK] phase 1 done.")


if __name__ == "__main__":
    main()
