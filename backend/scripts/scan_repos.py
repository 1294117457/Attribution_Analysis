"""扫描所有 repo 用了哪些 ORM 类，按库归类"""
import os
import re
import ast

ROOT = r"D:\codes\Attribution_Analysis\backend\src\contexts"
files = []
for sub in ("market", "concept", "user"):
    p = os.path.join(ROOT, sub, "infrastructure/persistence/repositories")
    if os.path.exists(p):
        for f in os.listdir(p):
            if f.endswith(".py") and not f.startswith("_"):
                files.append(os.path.join(p, f))

for full in sorted(files):
    with open(full, "r", encoding="utf-8") as f:
        src = f.read()
    # 找 import 的 ORM 类
    tree = ast.parse(src)
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.ImportFrom, ast.Import)):
            for n in node.names:
                imports.add(n.name)
    raw_orm = {x for x in imports if any(x.startswith(p) for p in (
        "StockInfoDB", "TechKlineDailyDB", "FinDailyBasicDB", "FinReportDB",
        "FinTop10", "FinTop10Float", "BaseDividend", "BaseAdjFactor", "BaseNameChange",
        "BaseSuspend", "MktIndexMember", "MktSectorDaily", "MktMarketDaily",
        "MktCalendar", "CapMoneyflow", "CapMargin", "CapMarginDetail", "CapTopList",
        "CapTopInst", "CapBlockTrade", "CapHolderNum",
        "ConceptsDB", "ConceptMemberDB", "ConceptIndexTHDB", "ConceptSnapshotDB",
    ))}
    attr_orm = {x for x in imports if any(x.startswith(p) for p in (
        "StockPool", "UserDB", "RoleDB", "CollectJob", "CollectDataPort",
        "PoolOperation",
    ))}
    rel = os.path.relpath(full, ROOT)
    print(f"{rel:60s}  raw={len(raw_orm):2d}  attr={len(attr_orm):2d}  {sorted(attr_orm) or '-'}")
