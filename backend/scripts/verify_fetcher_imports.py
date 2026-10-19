"""检查所有 fetcher 与 BO 能否正常 import

用法: python -m scripts.verify_fetcher_imports
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

errors: list[str] = []
oks: list[str] = []

# 检查 BO
try:
    from contexts.collect.application.bo import (
        BaseAdjFactorBO, BaseSuspendBO, BaseNameChangeBO, BaseDividendBO,
        CapMoneyflowBO, CapMoneyflowHsgtBO, CapHsgtTop10BO, CapLimitListDBO,
        CapMarginDetailBO, CapTopListBO, CapTopInstBO,
        CapBlockTradeBO, CapHolderNumBO,
        FinDailyBasicBO, FinReportBO,
        FinTop10HoldersBO, FinTop10FloatHoldersBO,
    )
    oks.append("BO: 13 个 capital + 2 个 fundamental + 4 个 tech = 19 个 BO 全部 import OK")
except Exception as e:
    errors.append(f"BO import 失败: {e!r}")

# 检查 concept BO
try:
    from contexts.concept.application.bo.concept import (
        ConceptListBO, ConceptMemberBO, ConceptOfStockBO,
        ConceptIndexTHBO, ConceptSnapshotBO, ConceptMinuteBO, ConceptMinutePoint,
    )
    oks.append("BO: 7 个 concept BO 全部 import OK")
except Exception as e:
    errors.append(f"concept BO import 失败: {e!r}")

# 检查 stock_info BO
try:
    from contexts.market.application.bo.stock_info import StockInfoBO
    # 验证 4 字段都存在
    required = ["fullname", "enname", "cnspell", "curr_type"]
    missing = [f for f in required if f not in StockInfoBO.model_fields]
    if missing:
        errors.append(f"StockInfoBO 缺字段: {missing}")
    else:
        oks.append("StockInfoBO 4 新字段 OK")
except Exception as e:
    errors.append(f"StockInfoBO import 失败: {e!r}")

# 检查 fetcher
FETCHERS = [
    "tech.DailyKlineTushareFetcher",
    "tech.SuspendTushareFetcher",
    "tech.AdjFactorTushareFetcher",
    "tech.NameChangeTushareFetcher",
    "tech.MinuteKlinePytdxFetcher",
    "fundamental.StockBasicTushareFetcher",
    "fundamental.FinIncomeTushareFetcher",
    "fundamental.DividendTushareFetcher",
    "fundamental.DailyBasicTushareFetcher",
    "fundamental.Top10HoldersTushareFetcher",
    "fundamental.Top10FloatHoldersTushareFetcher",
    "capital.MoneyflowTushareFetcher",
    "capital.MoneyflowHsgtTushareFetcher",
    "capital.TopListTushareFetcher",
    "capital.TopInstTushareFetcher",
    "capital.BlockTradeTushareFetcher",
    "capital.MarginDetailTushareFetcher",
    "capital.LimitListTushareFetcher",
    "capital.HsgtTop10TushareFetcher",
    "capital.HolderNumberTushareFetcher",
    "news.NewsTushareFetcher",
    "fundamental.ConceptListAdataFetcher",
    "fundamental.ConceptMembersAdataFetcher",
    "fundamental.ConceptIndexDailyAdataFetcher",
    "fundamental.ConceptSnapshotAdataFetcher",
    "fundamental.ConceptMinuteAdataFetcher",
    "fundamental.StockConceptsAdataFetcher",
]

for path in FETCHERS:
    module_path = f"contexts.collect.infrastructure.fetcher.{path}"
    try:
        __import__(module_path)
        oks.append(f"fetcher: {path}")
    except Exception as e:
        errors.append(f"fetcher {path} import 失败: {e!r}")

print("=" * 70)
print(f"OK: {len(oks)} / ERR: {len(errors)}")
print("=" * 70)
for ok in oks:
    print(f"  [OK ] {ok}")
for e in errors:
    print(f"  [ERR] {e}")

if errors:
    print("\n❌ 有失败")
    sys.exit(1)
print("\n✅ 全部 import OK")
