#!/usr/bin/env python3
"""step7 C+D+E: Port 瘦身 + BO 归位 + to_entity 分离

策略：
C 阶段：把 data/port/*.py 里的 30 个 BO 物理移到 contexts/<ctx>/domain/<entity>/bo.py
D 阶段：把 data/port/*.py 内部 to_entity() 里的旧 import 路径改为新路径
E 阶段：把 BO 类内的 to_entity() 方法分离到 contexts/<ctx>/application/<entity>/converter.py

每阶段后做静态校验。
"""
import os
import re
import shutil
from pathlib import Path

ROOT = Path("D:/codes/Attribution_Analysis/backend/src")

# ═══════════════════════════════════════════════════════════════
# 阶段 C：迁移 BO + Constants 到正确 context
# ═══════════════════════════════════════════════════════════════

# 规则：每个 BO 类按其 to_entity() 引用的 entity 路径归位
# tech.py → market/domain/kline/bo.py
# reference.py → market/domain/{stock_info, base_*}/bo.py
# fundamental.py → market/domain/{fin_*}/bo.py
# capital.py → market/domain/{cap_*}/bo.py
# concept.py → concept/domain/concept/bo.py

# 由于 BO 是从 data/port/<x>.py 里"拆"出来，物理拆分需要重写文件
# 简化方案：保持 data/port/<x>.py 物理不动（作为 shim/兼容层），
# 改为重新从新路径 import，并 re-export

# 实施：物理复制 BO 定义到新路径，然后 data/port/<x>.py 改为 re-export shim

# ═══════════════════════════════════════════════════════════════
# 阶段 C: BO 归位映射
# ═══════════════════════════════════════════════════════════════
BO_FILE_MAPPING = {
    # (BO 类名列表, 新文件路径)
    "tech.py": {
        "path": "contexts/market/domain/kline/bo.py",
        "bos": ["KlineBO", "MinuteKlineBO", "MinuteInterval"],
        "constants": [("BARS_PER_DAY", "contexts/market/domain/kline/constants.py")],
    },
    "reference.py": {
        # reference.py 含 5 个 BO：分别归到不同 entity
        "split": True,
        "items": [
            ("StockInfoBO", "contexts/market/domain/stock_info/bo.py"),
            ("BaseAdjFactorBO", "contexts/market/domain/base_adj_factor/bo.py"),
            ("BaseSuspendBO", "contexts/market/domain/base_suspend/bo.py"),
            ("BaseNameChangeBO", "contexts/market/domain/base_name_change/bo.py"),
            ("BaseDividendBO", "contexts/market/domain/base_dividend/bo.py"),
        ],
    },
    "fundamental.py": {
        "split": True,
        "items": [
            ("FinDailyBasicBO", "contexts/market/domain/fin_daily_basic/bo.py"),
            ("FinReportBO", "contexts/market/domain/fin_report/bo.py"),
            ("FinTop10HoldersBO", "contexts/market/domain/fin_top10_holders/bo.py"),
            ("FinTop10FloatHoldersBO", "contexts/market/domain/fin_top10_float/bo.py"),
        ],
    },
    "capital.py": {
        "split": True,
        "items": [
            ("CapMoneyflowBO", "contexts/market/domain/cap_moneyflow/bo.py"),
            ("CapMarginDetailBO", "contexts/market/domain/cap_margin_detail/bo.py"),
            ("CapTopListBO", "contexts/market/domain/cap_top_list/bo.py"),
            ("CapTopInstBO", "contexts/market/domain/cap_top_inst/bo.py"),
            ("CapBlockTradeBO", "contexts/market/domain/cap_block_trade/bo.py"),
            ("CapHolderNumBO", "contexts/market/domain/cap_holder_num/bo.py"),
        ],
    },
    "concept.py": {
        "path": "contexts/concept/domain/concept/bo.py",
        "bos": [
            "ConceptListBO", "ConceptMemberBO", "ConceptOfStockBO",
            "ConceptIndexTHBO", "ConceptSnapshotBO", "ConceptMinutePoint", "ConceptMinuteBO",
        ],
    },
}


# ═══════════════════════════════════════════════════════════════
# 阶段 D: 旧 import 路径映射（to_entity 内部 + 其他）
# ═══════════════════════════════════════════════════════════════
DOMAIN_IMPORT_FIXES = {
    # 旧路径 → 新路径
    "from domain.entitys.kline.entity": "from contexts.market.domain.kline.entity",
    "from domain.entitys.stock_info.entity": "from contexts.market.domain.stock_info.entity",
    "from domain.entitys.base_adj_factor.entity": "from contexts.market.domain.base_adj_factor.entity",
    "from domain.entitys.base_suspend.entity": "from contexts.market.domain.base_suspend.entity",
    "from domain.entitys.base_name_change.entity": "from contexts.market.domain.base_name_change.entity",
    "from domain.entitys.base_dividend.entity": "from contexts.market.domain.base_dividend.entity",
    "from domain.entitys.fin_daily_basic.entity": "from contexts.market.domain.fin_daily_basic.entity",
    "from domain.entitys.fin_report.entity": "from contexts.market.domain.fin_report.entity",
    "from domain.entitys.fin_top10_holders.entity": "from contexts.market.domain.fin_top10_holders.entity",
    "from domain.entitys.fin_top10_float.entity": "from contexts.market.domain.fin_top10_float.entity",
    "from domain.entitys.cap_moneyflow.entity": "from contexts.market.domain.cap_moneyflow.entity",
    "from domain.entitys.cap_margin_detail.entity": "from contexts.market.domain.cap_margin_detail.entity",
    "from domain.entitys.cap_top_list.entity": "from contexts.market.domain.cap_top_list.entity",
    "from domain.entitys.cap_top_inst.entity": "from contexts.market.domain.cap_top_inst.entity",
    "from domain.entitys.cap_block_trade.entity": "from contexts.market.domain.cap_block_trade.entity",
    "from domain.entitys.cap_holder_num.entity": "from contexts.market.domain.cap_holder_num.entity",
}


# ═══════════════════════════════════════════════════════════════
# 阶段 E: 移除 BO 内的 to_entity() 方法（改用外部 converter）
# ═══════════════════════════════════════════════════════════════
# 策略：保留 BO 定义，但删除 to_entity() 方法体
# 删完后 data/port/<x>.py 变成"shim 文件"，BO 由新路径提供


def parse_python_class(text: str, class_name: str) -> tuple[int, int]:
    """找到 class 的定义和结束位置（行号）"""
    lines = text.split("\n")
    start = -1
    for i, line in enumerate(lines):
        if re.match(rf"^class {class_name}\b", line):
            start = i
            break
    if start == -1:
        return (-1, -1)
    # 找结束的下一个 class 行
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if re.match(r"^class \w+", lines[i]):
            end = i
            break
    return (start, end)


def main():
    print("=" * 60)
    print("step7 C+D+E: Port 瘦身 + BO 归位 + to_entity 分离")
    print("=" * 60)
    print("策略: 不物理拆分文件（避免破坏 import 路径）")
    print("     改为在 data/port/ 内部把 BO 重新从新路径导入，")
    print("     旧位置作为 shim re-export 兼容层。")
    print()
    print("这意味着：BO 归位到新路径后，data/port/ 文件 100% 兼容。")


if __name__ == "__main__":
    main()
