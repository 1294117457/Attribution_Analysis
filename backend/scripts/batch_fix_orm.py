"""批量改 ORM：
1. import: from .orm_base import Base → from .orm_base import RawBase
2. class Foo(Base) → class Foo(RawBase)
3. __tablename__ = "old_name" → __tablename__ = "new_name"

只对 raw_data_db 的 22 张表做，对 attribution_db 的表（user/role/pool/collect_job/collect_data_port）不动。
"""
import os
import re

ROOT = r"D:\codes\Attribution_Analysis\backend\src"

# 22 个 ORM 文件（raw_data_db）及其新表名
RAW_ORM_FILES = {
    "contexts/market/infrastructure/persistence/models/stock_info.py": "fundamental_stock_info",
    "contexts/market/infrastructure/persistence/models/fin_daily_basic.py": "fundamental_daily_basic",
    "contexts/market/infrastructure/persistence/models/fin_report.py": "fundamental_report",
    "contexts/market/infrastructure/persistence/models/fin_top10_holders.py": "fundamental_top10",
    "contexts/market/infrastructure/persistence/models/fin_top10_float.py": "fundamental_top10_float",
    "contexts/market/infrastructure/persistence/models/base_dividend.py": "fundamental_dividend",
    "contexts/market/infrastructure/persistence/models/mkt_index_member.py": "fundamental_index_member",
    "contexts/market/infrastructure/persistence/models/mkt_sector_daily.py": "fundamental_sector_daily",
    "contexts/market/infrastructure/persistence/models/mkt_market_daily.py": "fundamental_market_daily",
    "contexts/market/infrastructure/persistence/models/tech_kline.py": "tech_kline_daily",
    "contexts/market/infrastructure/persistence/models/base_adj_factor.py": "tech_adj_factor",
    "contexts/market/infrastructure/persistence/models/base_name_change.py": "tech_name_change",
    "contexts/market/infrastructure/persistence/models/base_suspend.py": "tech_suspend",
    "contexts/market/infrastructure/persistence/models/mkt_calendar.py": "tech_calendar",
    "contexts/market/infrastructure/persistence/models/cap_moneyflow.py": "capital_moneyflow",
    "contexts/market/infrastructure/persistence/models/cap_margin_detail.py": "capital_margin_detail",
    "contexts/market/infrastructure/persistence/models/cap_margin.py": "capital_margin",
    "contexts/market/infrastructure/persistence/models/cap_top_list.py": "capital_top_list",
    "contexts/market/infrastructure/persistence/models/cap_top_inst.py": "capital_top_inst",
    "contexts/market/infrastructure/persistence/models/cap_block_trade.py": "capital_block_trade",
    "contexts/market/infrastructure/persistence/models/cap_holder_num.py": "capital_holder_num",
}

# concept.py 包含 4 个类（同一文件）
CONCEPT_RAW_CLASSES = {
    "ConceptDB": "fundamental_concept",
    "ConceptMemberDB": "fundamental_concept_member",
    "ConceptIndexKlineDB": "fundamental_concept_index",
    "ConceptSnapshotDB": "fundamental_concept_snapshot",
}

# 这些是 attribution_db 的表，不动
ATTRIB_ORM_FILES = {
    "contexts/auth/infrastructure/persistence/models/user.py",
    "contexts/auth/infrastructure/persistence/models/user_role.py",
    "contexts/user/infrastructure/persistence/models/pool.py",
    "contexts/collect/infrastructure/persistence/models/collect_data_port.py",
    "contexts/collect/infrastructure/persistence/models/collect_job.py",
}

for rel_path, new_tablename in RAW_ORM_FILES.items():
    full = os.path.join(ROOT, rel_path)
    if not os.path.exists(full):
        print(f"!! 缺失: {rel_path}")
        continue
    with open(full, "r", encoding="utf-8") as f:
        src = f.read()

    orig = src
    # 1) import:  Base → RawBase
    src = src.replace(
        "from shared.infrastructure.persistence.orm_base import Base",
        "from shared.infrastructure.persistence.orm_base import RawBase",
    )
    # 2) class XXX(Base, ...) → class XXX(RawBase, ...)
    src = re.sub(r"class\s+(\w+)\(Base(\s*,)", r"class \1(RawBase\2", src)
    src = re.sub(r"class\s+(\w+)\(Base\)", r"class \1(RawBase)", src)
    # 3) __tablename__
    src = re.sub(
        r'__tablename__\s*=\s*"[^"]+"',
        f'__tablename__ = "{new_tablename}"',
        src,
    )

    if src != orig:
        with open(full, "w", encoding="utf-8") as f:
            f.write(src)
        print(f"OK  {rel_path}  →  {new_tablename}")
    else:
        print(f"--  {rel_path}  无变化")

# 单独处理 concept.py（4 个类）
concept_file = os.path.join(ROOT, "contexts/concept/infrastructure/persistence/models/concept.py")
if os.path.exists(concept_file):
    with open(concept_file, "r", encoding="utf-8") as f:
        src = f.read()
    orig = src
    # import
    src = src.replace(
        "from shared.infrastructure.persistence.orm_base import Base",
        "from shared.infrastructure.persistence.orm_base import RawBase",
    )
    # class
    src = re.sub(r"class\s+(\w+)\(Base(\s*,)", r"class \1(RawBase\2", src)
    src = re.sub(r"class\s+(\w+)\(Base\)", r"class \1(RawBase)", src)
    # 找所有 __tablename__，按顺序映射
    names = list(CONCEPT_RAW_CLASSES.values())
    counter = [0]

    def replace_tn(m):
        if counter[0] < len(names):
            new = names[counter[0]]
            counter[0] += 1
            return f'__tablename__ = "{new}"'
        return m.group(0)

    src = re.sub(r'__tablename__\s*=\s*"[^"]+"', replace_tn, src)
    if src != orig:
        with open(concept_file, "w", encoding="utf-8") as f:
            f.write(src)
        print(f"OK  concept.py  →  {names}")
    else:
        print(f"--  concept.py  无变化")
else:
    print("!! 缺失: concept.py")

print("\n完成。")
