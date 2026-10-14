#!/usr/bin/env python3
"""step7 C-2: 把 data/port/<x>.py 改为 shim re-export

策略：
- 删除 data/port/<x>.py 里的 BO 类定义
- 改为 `from contexts.<ctx>.domain.<entity>.bo import <BO>` 形式
- 保留 Params / Port / 类型别名在 data/port/<x>.py
- 这样调用方代码（raw_store.py 等）继续工作
"""
import os
import re
from pathlib import Path

ROOT = Path("D:/codes/Attribution_Analysis/backend/src")

# 源文件 → 需要从新位置 re-export 的 BO 列表
SHIM_REWRITES = {
    "contexts/data/application/port/tech.py": {
        "imports": [
            "from contexts.market.domain.kline.bo import KlineBO, MinuteKlineBO, MinuteInterval, BARS_PER_DAY",
        ],
        "remove_classes": ["KlineBO", "MinuteKlineBO", "MinuteInterval"],
        "remove_constant": "BARS_PER_DAY",
    },
    "contexts/data/application/port/reference.py": {
        "imports": [
            "from contexts.market.domain.stock_info.bo import StockInfoBO",
            "from contexts.market.domain.base_adj_factor.bo import BaseAdjFactorBO",
            "from contexts.market.domain.base_suspend.bo import BaseSuspendBO",
            "from contexts.market.domain.base_name_change.bo import BaseNameChangeBO",
            "from contexts.market.domain.base_dividend.bo import BaseDividendBO",
        ],
        "remove_classes": ["StockInfoBO", "BaseAdjFactorBO", "BaseSuspendBO", "BaseNameChangeBO", "BaseDividendBO"],
    },
    "contexts/data/application/port/fundamental.py": {
        "imports": [
            "from contexts.market.domain.fin_daily_basic.bo import FinDailyBasicBO",
            "from contexts.market.domain.fin_report.bo import FinReportBO",
            "from contexts.market.domain.fin_top10_holders.bo import FinTop10HoldersBO",
            "from contexts.market.domain.fin_top10_float.bo import FinTop10FloatHoldersBO",
        ],
        "remove_classes": ["FinDailyBasicBO", "FinReportBO", "FinTop10HoldersBO", "FinTop10FloatHoldersBO"],
    },
    "contexts/data/application/port/capital.py": {
        "imports": [
            "from contexts.market.domain.cap_moneyflow.bo import CapMoneyflowBO",
            "from contexts.market.domain.cap_margin_detail.bo import CapMarginDetailBO",
            "from contexts.market.domain.cap_top_list.bo import CapTopListBO",
            "from contexts.market.domain.cap_top_inst.bo import CapTopInstBO",
            "from contexts.market.domain.cap_block_trade.bo import CapBlockTradeBO",
            "from contexts.market.domain.cap_holder_num.bo import CapHolderNumBO",
        ],
        "remove_classes": ["CapMoneyflowBO", "CapMarginDetailBO", "CapTopListBO", "CapTopInstBO", "CapBlockTradeBO", "CapHolderNumBO"],
    },
    "contexts/data/application/port/concept.py": {
        "imports": [
            "from contexts.concept.domain.concept.bo import ConceptListBO, ConceptMemberBO, ConceptOfStockBO, ConceptIndexTHBO, ConceptSnapshotBO, ConceptMinutePoint, ConceptMinuteBO",
        ],
        "remove_classes": ["ConceptListBO", "ConceptMemberBO", "ConceptOfStockBO", "ConceptIndexTHBO", "ConceptSnapshotBO", "ConceptMinutePoint", "ConceptMinuteBO"],
    },
}


def remove_class_block(text: str, class_name: str) -> str:
    """删除 class 定义块"""
    lines = text.split("\n")
    start = -1
    for i, line in enumerate(lines):
        if re.match(rf"^class {class_name}\b", line):
            start = i
            break
    if start == -1:
        return text
    # 找结束（下一个 class 或文件末尾）
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if re.match(r"^class \w+", lines[i]):
            end = i
            break
    # 删整段 + 后面空行
    while end < len(lines) and lines[end].strip() == "":
        end += 1
    new_lines = lines[:start] + lines[end:]
    return "\n".join(new_lines)


def remove_constant_block(text: str, const_name: str) -> str:
    """删除 BARS_PER_DAY 这种模块级常量"""
    pattern = rf"^{const_name}\s*:\s*dict\[.*?\]?\s*=\s*\{{[^}}]*\}}.*?\n"
    return re.sub(pattern, "", text, flags=re.MULTILINE | re.DOTALL)


def do_shim():
    for src, cfg in SHIM_REWRITES.items():
        src_p = ROOT / src
        if not src_p.exists():
            print(f"  SKIP (源不存在): {src}")
            continue

        text = src_p.read_text(encoding="utf-8")
        original = text

        # 1. 删除 class 块
        for cls in cfg.get("remove_classes", []):
            text = remove_class_block(text, cls)

        # 2. 删除常量块
        if "remove_constant" in cfg:
            text = remove_constant_block(text, cfg["remove_constant"])

        # 3. 删完后，需要在 `from __future__` 后面插入 re-export imports
        # 找第一个 `from ` 或 `import ` 之外的非空行之后
        lines = text.split("\n")
        # 找到所有 from ... import 行的位置
        last_import_idx = -1
        for i, line in enumerate(lines):
            if line.startswith("from ") or line.startswith("import "):
                last_import_idx = i

        if last_import_idx == -1:
            # 没有 import，直接加
            insert_idx = 0
        else:
            insert_idx = last_import_idx + 1

        # 在 import 后加空行 + re-export
        new_imports = ["", ""] + cfg["imports"] + [""]
        lines = lines[:insert_idx] + new_imports + lines[insert_idx:]
        text = "\n".join(lines)

        # 4. 清理（多个连续空行 → 一个）
        text = re.sub(r"\n{3,}", "\n\n", text)

        if text != original:
            src_p.write_text(text, encoding="utf-8")
            print(f"  SHIM: {src}")
        else:
            print(f"  NO-CHANGE: {src}")


def main():
    print("=" * 60)
    print("step7 C-2: data/port/ 改为 shim re-export")
    print("=" * 60)
    print()
    do_shim()


if __name__ == "__main__":
    main()
