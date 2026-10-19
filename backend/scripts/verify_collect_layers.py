"""import 验证脚本

检查 collect context 全部 25 个 repo + 25 个 service + 5 个 route + DI 是否能 import。
"""
import sys
import os

# 切换到 backend 工作目录，并把 src 加进 sys.path（与 verify_fetcher_imports 一致）
ROOT = r"D:\codes\Attribution_Analysis\backend"
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

# 按 facet 顺序统计
results = {
    "repo": [],
    "service": [],
    "di": [],
    "route": [],
    "domain_protocol": [],
}

errors: list[tuple[str, str, Exception]] = []


def try_import(label: str, modpath: str, target_list: list[str]) -> None:
    try:
        mod = __import__(modpath, fromlist=["__name__"])
        for name in target_list:
            if not hasattr(mod, name):
                raise RuntimeError(f"缺少 {name}")
        results[label].append((modpath, "OK", target_list))
    except Exception as e:
        results[label].append((modpath, "FAIL", [str(e)][:1]))
        errors.append((label, modpath, e))


# ───── 25 个 repo ─────
repos = [
    ("contexts.collect.infrastructure.persistence.repositories",
     ["KlineRepository", "StockInfoRepository", "AdjFactorRepository", "SuspendRepository",
      "NameChangeRepository", "DividendRepository", "MoneyflowRepository",
      "MoneyflowHsgtRepository", "TopListRepository", "TopInstRepository",
      "BlockTradeRepository", "MarginDetailRepository", "HsgtTop10Repository",
      "LimitListRepository", "HolderNumberRepository", "FinDailyBasicRepository",
      "FinReportRepository", "FinTop10HoldersRepository", "FinTop10FloatHoldersRepository",
      "StockConceptRepository", "ConceptRepository", "ConceptMemberRepository",
      "ConceptIndexRepository", "ConceptSnapshotRepository", "NewsArticleRepository"]),
]
for modpath, names in repos:
    try_import("repo", modpath, names)

# ───── 25 个 service ─────
svc_specs = [
    ("contexts.collect.application.service.tech.daily_kline_service", ["DailyKlineService"]),
    ("contexts.collect.application.service.tech.minute_kline_service", ["MinuteKlineService"]),
    ("contexts.collect.application.service.tech.adj_factor_service", ["AdjFactorService"]),
    ("contexts.collect.application.service.tech.suspend_service", ["SuspendService"]),
    ("contexts.collect.application.service.tech.name_change_service", ["NameChangeService"]),
    ("contexts.collect.application.service.capital.moneyflow_service", ["MoneyflowService"]),
    ("contexts.collect.application.service.capital.moneyflow_hsgt_service", ["MoneyflowHsgtService"]),
    ("contexts.collect.application.service.capital.top_list_service", ["TopListService"]),
    ("contexts.collect.application.service.capital.top_inst_service", ["TopInstService"]),
    ("contexts.collect.application.service.capital.block_trade_service", ["BlockTradeService"]),
    ("contexts.collect.application.service.capital.margin_service", ["MarginService"]),
    ("contexts.collect.application.service.capital.hsgt_top10_service", ["HsgtTop10Service"]),
    ("contexts.collect.application.service.capital.limit_list_service", ["LimitListService"]),
    ("contexts.collect.application.service.capital.holder_number_service", ["HolderNumberService"]),
    ("contexts.collect.application.service.fundamental.daily_basic_service", ["DailyBasicService"]),
    ("contexts.collect.application.service.fundamental.fin_income_service", ["FinIncomeService"]),
    ("contexts.collect.application.service.fundamental.top10_holders_service", ["Top10HoldersService"]),
    ("contexts.collect.application.service.fundamental.top10_floatholders_service", ["Top10FloatHoldersService"]),
    ("contexts.collect.application.service.fundamental.dividend_service", ["DividendService"]),
    ("contexts.collect.application.service.news.news_service", ["NewsService"]),
    ("contexts.collect.application.service.fundamental.stock_basic_service", ["StockBasicService"]),
    ("contexts.collect.application.service.fundamental.stock_concepts_service", ["StockConceptsService"]),
    ("contexts.collect.application.service.fundamental.concept_list_service", ["ConceptListService"]),
    ("contexts.collect.application.service.fundamental.concept_members_service", ["ConceptMembersService"]),
    ("contexts.collect.application.service.fundamental.concept_index_daily_service", ["ConceptIndexDailyService"]),
    ("contexts.collect.application.service.fundamental.concept_snapshot_service", ["ConceptSnapshotService"]),
    ("contexts.collect.application.service.fundamental.concept_minute_service", ["ConceptMinuteService"]),
    ("contexts.collect.application.service.sentiment.sentiment_service", ["SentimentService"]),
]
for modpath, names in svc_specs:
    try_import("service", modpath, names)

# ───── DI ─────
di_specs = [
    ("contexts.collect.infrastructure.di.repo", [
        "get_kline_repository", "get_adj_factor_repository", "get_suspend_repository",
        "get_name_change_repository", "get_dividend_repository",
        "get_moneyflow_repository", "get_moneyflow_hsgt_repository",
        "get_top_list_repository", "get_top_inst_repository",
        "get_block_trade_repository", "get_margin_detail_repository",
        "get_hsgt_top10_repository", "get_limit_list_repository",
        "get_holder_number_repository", "get_fin_daily_basic_repository",
        "get_fin_report_repository", "get_fin_top10_holders_repository",
        "get_fin_top10_float_holders_repository", "get_stock_concept_repository",
        "get_concept_repository", "get_concept_member_repository",
        "get_concept_index_repository", "get_concept_snapshot_repository",
        "get_news_article_repository", "get_stock_info_repository",
    ]),
    ("contexts.collect.infrastructure.di.collect_service", [
        "get_daily_kline_service", "get_minute_kline_service", "get_adj_factor_service",
        "get_suspend_service", "get_name_change_service",
        "get_moneyflow_service", "get_moneyflow_hsgt_service", "get_top_list_service",
        "get_top_inst_service", "get_block_trade_service", "get_margin_service",
        "get_hsgt_top10_service", "get_limit_list_service", "get_holder_number_service",
        "get_daily_basic_service", "get_fin_income_service", "get_top10_holders_service",
        "get_top10_float_holders_service", "get_dividend_service", "get_stock_basic_service",
        "get_stock_concepts_service", "get_concept_list_service", "get_concept_members_service",
        "get_concept_index_daily_service", "get_concept_minute_service", "get_concept_snapshot_service",
        "get_news_service", "get_sentiment_service",
    ]),
]
for modpath, names in di_specs:
    try_import("di", modpath, names)

# ───── 5 route ─────
route_specs = [
    ("contexts.collect.interface.route.tech", ["router"]),
    ("contexts.collect.interface.route.capital", ["router"]),
    ("contexts.collect.interface.route.fundamental", ["router"]),
    ("contexts.collect.interface.route.news", ["router"]),
    ("contexts.collect.interface.route.sentiment", ["router"]),
]
for modpath, names in route_specs:
    try_import("route", modpath, names)

# ───── DTO ─────
dto_specs = [
    ("contexts.collect.interface.dto.request.collect", ["CollectRequest"]),
    ("contexts.collect.interface.dto.response.collect", ["CollectResponse"]),
]
for modpath, names in dto_specs:
    try_import("route", modpath, names)

# ───── 25 domain Protocol ─────
proto_specs = [
    ("contexts.collect.domain.entitys.adj_factor.repository", ["AdjFactorRepository"]),
    ("contexts.collect.domain.entitys.suspend.repository", ["SuspendRepository"]),
    ("contexts.collect.domain.entitys.name_change.repository", ["NameChangeRepository"]),
    ("contexts.collect.domain.entitys.dividend.repository", ["DividendRepository"]),
    ("contexts.collect.domain.entitys.moneyflow.repository", ["MoneyflowRepository"]),
    ("contexts.collect.domain.entitys.moneyflow_hsgt.repository", ["MoneyflowHsgtRepository"]),
    ("contexts.collect.domain.entitys.top_list.repository", ["TopListRepository"]),
    ("contexts.collect.domain.entitys.top_inst.repository", ["TopInstRepository"]),
    ("contexts.collect.domain.entitys.block_trade.repository", ["BlockTradeRepository"]),
    ("contexts.collect.domain.entitys.margin_detail.repository", ["MarginDetailRepository"]),
    ("contexts.collect.domain.entitys.hsgt_top10.repository", ["HsgtTop10Repository"]),
    ("contexts.collect.domain.entitys.limit_list.repository", ["LimitListRepository"]),
    ("contexts.collect.domain.entitys.holder_number.repository", ["HolderNumberRepository"]),
    ("contexts.collect.domain.entitys.fin_daily_basic.repository", ["FinDailyBasicRepository"]),
    ("contexts.collect.domain.entitys.fin_report.repository", ["FinReportRepository"]),
    ("contexts.collect.domain.entitys.fin_top10_holders.repository", ["FinTop10HoldersRepository"]),
    ("contexts.collect.domain.entitys.fin_top10_float_holders.repository", ["FinTop10FloatHoldersRepository"]),
    ("contexts.collect.domain.entitys.stock_concept.repository", ["StockConceptRepository"]),
    ("contexts.collect.domain.entitys.concept.repository", ["ConceptRepository"]),
    ("contexts.collect.domain.entitys.concept_member.repository", ["ConceptMemberRepository"]),
    ("contexts.collect.domain.entitys.concept_index.repository", ["ConceptIndexRepository"]),
    ("contexts.collect.domain.entitys.concept_snapshot.repository", ["ConceptSnapshotRepository"]),
    ("contexts.collect.domain.entitys.news_article.repository", ["NewsArticleRepository"]),
]
for modpath, names in proto_specs:
    try_import("domain_protocol", modpath, names)


# ───── 报告 ─────
print("\n" + "=" * 60)
print("Collect 三层同步 import 验证报告")
print("=" * 60)
total_ok = 0
total_fail = 0
for label, items in results.items():
    ok = sum(1 for _, s, _ in items if s == "OK")
    fail = sum(1 for _, s, _ in items if s != "OK")
    total_ok += ok
    total_fail += fail
    print(f"[{label:<18}] OK={ok:>3}  FAIL={fail:>3}")
    for modpath, status, _ in items:
        if status != "OK":
            print(f"  FAIL: {modpath}  — {_}")
print("=" * 60)
print(f"总计 OK={total_ok}  FAIL={total_fail}")
print("=" * 60)

if total_fail:
    print("\n失败列表：")
    for label, modpath, e in errors:
        print(f"  [{label}] {modpath}: {e!r}")
    sys.exit(1)
else:
    print("\n所有 import 通过 ✅")
    sys.exit(0)
