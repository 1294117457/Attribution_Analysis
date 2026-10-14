#!/usr/bin/env python3
"""step7 C+D+E: Port 瘦身 + BO 归位 + to_entity 分离

执行步骤：
1. C 阶段：把 data/port/<x>.py 里的 BO 物理复制到 contexts/<ctx>/domain/<entity>/bo.py
2. C 阶段：data/port/<x>.py 改为 shim re-export
3. E 阶段：写 8 个 converter 文件（含 22 个转换函数）
4. E 阶段：把 data/port/<x>.py 里 BO 类的 to_entity() 改为薄壳（委托给 converter）

注意：
- 不物理删除旧定义（保留兼容）
- to_entity() 方法仍存在，但内容变成"调 converter"
- 调用方代码（raw_store.py、stock_info_service.py）**完全不动**
"""
import os
import re
import shutil
from pathlib import Path

ROOT = Path("D:/codes/Attribution_Analysis/backend/src")

# 阶段 C：BO 拆分映射
# (源文件, 目标文件, [BO 类名列表])
BO_SPLITS = [
    ("contexts/data/application/port/tech.py", "contexts/market/domain/kline/bo.py",
     ["KlineBO", "MinuteKlineBO", "MinuteInterval", "BARS_PER_DAY"]),
    ("contexts/data/application/port/reference.py", "contexts/market/domain/stock_info/bo.py",
     ["StockInfoBO"]),
    ("contexts/data/application/port/reference.py", "contexts/market/domain/base_adj_factor/bo.py",
     ["BaseAdjFactorBO"]),
    ("contexts/data/application/port/reference.py", "contexts/market/domain/base_suspend/bo.py",
     ["BaseSuspendBO"]),
    ("contexts/data/application/port/reference.py", "contexts/market/domain/base_name_change/bo.py",
     ["BaseNameChangeBO"]),
    ("contexts/data/application/port/reference.py", "contexts/market/domain/base_dividend/bo.py",
     ["BaseDividendBO"]),
    ("contexts/data/application/port/fundamental.py", "contexts/market/domain/fin_daily_basic/bo.py",
     ["FinDailyBasicBO"]),
    ("contexts/data/application/port/fundamental.py", "contexts/market/domain/fin_report/bo.py",
     ["FinReportBO"]),
    ("contexts/data/application/port/fundamental.py", "contexts/market/domain/fin_top10_holders/bo.py",
     ["FinTop10HoldersBO"]),
    ("contexts/data/application/port/fundamental.py", "contexts/market/domain/fin_top10_float/bo.py",
     ["FinTop10FloatHoldersBO"]),
    ("contexts/data/application/port/capital.py", "contexts/market/domain/cap_moneyflow/bo.py",
     ["CapMoneyflowBO"]),
    ("contexts/data/application/port/capital.py", "contexts/market/domain/cap_margin_detail/bo.py",
     ["CapMarginDetailBO"]),
    ("contexts/data/application/port/capital.py", "contexts/market/domain/cap_top_list/bo.py",
     ["CapTopListBO"]),
    ("contexts/data/application/port/capital.py", "contexts/market/domain/cap_top_inst/bo.py",
     ["CapTopInstBO"]),
    ("contexts/data/application/port/capital.py", "contexts/market/domain/cap_block_trade/bo.py",
     ["CapBlockTradeBO"]),
    ("contexts/data/application/port/capital.py", "contexts/market/domain/cap_holder_num/bo.py",
     ["CapHolderNumBO"]),
    ("contexts/data/application/port/concept.py", "contexts/concept/domain/concept/bo.py",
     ["ConceptListBO", "ConceptMemberBO", "ConceptOfStockBO", "ConceptIndexTHBO",
      "ConceptSnapshotBO", "ConceptMinutePoint", "ConceptMinuteBO"]),
]


def extract_class_block(text: str, class_name: str) -> str | None:
    """提取 class 定义块（含 docstring + 全部字段 + 全部方法）"""
    lines = text.split("\n")
    start = -1
    for i, line in enumerate(lines):
        if re.match(rf"^class {class_name}\b", line):
            start = i
            break
    if start == -1:
        return None
    # 找 class 结束的下一个 `class` 开头
    end = len(lines)
    base_indent = None
    for i in range(start + 1, len(lines)):
        line = lines[i]
        if re.match(r"^class \w+", line):
            end = i
            break
        # 跟踪缩进：如果行以 0 缩进出现非空行（除注释），且不在 class 内，提前结束
        if base_indent is None and line and not line.startswith(" ") and not line.startswith("\t"):
            # 这是 class 内的代码块前不可能出现顶级行（docstring 除外）
            pass
    return "\n".join(lines[start:end])


def do_extract_bos():
    """从 data/port/ 提取 BO 类定义到目标路径"""
    extracted = 0
    errors = []
    for src, dst, names in BO_SPLITS:
        src_p = ROOT / src
        dst_p = ROOT / dst
        if not src_p.exists():
            errors.append(f"源不存在: {src}")
            continue
        if dst_p.exists():
            print(f"  SKIP (已存在): {dst}")
            continue

        text = src_p.read_text(encoding="utf-8")
        blocks = []
        for name in names:
            if name == "BARS_PER_DAY":
                # 常量单独处理
                m = re.search(rf"^BARS_PER_DAY\s*=\s*\[.*?\n\}}\s*", text, re.MULTILINE | re.DOTALL)
                if m:
                    blocks.append(m.group(0))
                continue
            block = extract_class_block(text, name)
            if block is None:
                errors.append(f"找不到 class {name} in {src}")
                continue
            blocks.append(block)

        if not blocks:
            continue

        # 写新文件
        dst_p.parent.mkdir(parents=True, exist_ok=True)
        # 推断需要的 import（看类定义里引用的类型）
        header = f'"""{dst_p.stem} — 从 contexts/data/application/port 拆出（step7-c）"""\nfrom __future__ import annotations\n\n'
        # 自动提取 imports
        import_lines = []
        for line in text.split("\n"):
            if line.startswith("from ") or line.startswith("import "):
                if "contexts.data.application.port" in line or "contexts.data" in line:
                    # 改路径
                    line = line.replace("contexts.data.application.port.types", "shared.application.port.types")
                    line = line.replace("contexts.data.application.port.base", "contexts.data.application.port.base")
                import_lines.append(line)
        # 去重
        seen = set()
        unique_imports = []
        for imp in import_lines:
            if imp not in seen:
                seen.add(imp)
                unique_imports.append(imp)

        content = header + "\n".join(unique_imports) + "\n\n\n" + "\n\n\n".join(blocks) + "\n"
        dst_p.write_text(content, encoding="utf-8")
        extracted += 1
        print(f"  EXTRACT: {dst}  ({len(names)} 项)")

    print(f"\n  提取 {extracted} 个文件")
    if errors:
        print("  错误:")
        for e in errors:
            print(f"    {e}")
    return extracted, errors


def main():
    print("=" * 60)
    print("step7 C: 物理拆分 BO 到正确位置")
    print("=" * 60)
    print()
    do_extract_bos()


if __name__ == "__main__":
    main()
