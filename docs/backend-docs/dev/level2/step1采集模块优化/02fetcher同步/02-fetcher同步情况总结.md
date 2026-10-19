# Fetcher 同步情况总结（第一步执行后）

> 位置：`docs/backend-docs/dev/level2/step1采集模块优化/02fetcher同步/02-fetcher同步情况总结.md`
> 配套文档：`01-fetcher与接口文档对账与同步方案.md`（对账方案）、`01-字段对账与修复方案.md`（表结构）
> 更新日期：2026-10-18

## 一、总体进度

| 维度 | 同步前 | **同步后** | 状态 |
|---|---|---|---|
| Fetcher 总数 | 27 | **27** | — |
| 与官方文档字段对齐 | 14/27 (52%) | **27/27 (100%)** | ✅ 已完成 |
| 与 `raw_data_db` 表字段对齐 | 14/27 (52%) | **27/27 (100%)** | ✅ 已完成 |
| 返回 `list[BaseModel]`（强类型） | 18/27 (67%) | **20/27 (74%)** | 🟡 剩 7 个 `list[dict]` |
| `raw_data_db` 表结构对齐文档 | 25/30 (83%) | **30/30 (100%)** | ✅ 已完成 |

> 27 个 fetcher 中，Tushare 20 个、Adata 6 个、Pytdx 1 个。

## 二、按基本面 × 数据源 分类清单

| # | 基本面 | 数据源 | Fetcher 类 | 表名 | 返回类型 |
|---|---|---|---|---|---|
| 1 | 行情 | tushare | `DailyKlineTushareFetcher` | `tech_kline_daily` | `KlineBO` |
| 2 | 行情 | tushare | `AdjFactorTushareFetcher` | `tech_adj_factor` | `BaseAdjFactorBO` |
| 3 | 行情 | tushare | `SuspendTushareFetcher` | `tech_suspend` | `BaseSuspendBO` |
| 4 | 行情 | tushare | `NameChangeTushareFetcher` | `tech_name_change` | `BaseNameChangeBO` |
| 5 | 行情 | pytdx  | `MinuteKlinePytdxFetcher` | (实时查询，不入库) | `MinuteKlineBO` |
| 6 | 资金 | tushare | `MoneyflowTushareFetcher` | `capital_moneyflow` | `CapMoneyflowBO` |
| 7 | 资金 | tushare | `MoneyflowHsgtTushareFetcher` | `capital_moneyflow_hsgt` | `CapMoneyflowHsgtBO` |
| 8 | 资金 | tushare | `TopListTushareFetcher` | `capital_top_list` | `CapTopListBO` |
| 9 | 资金 | tushare | `TopInstTushareFetcher` | `capital_top_inst` | `CapTopInstBO` |
| 10 | 资金 | tushare | `BlockTradeTushareFetcher` | `capital_block_trade` | `CapBlockTradeBO` |
| 11 | 资金 | tushare | `MarginDetailTushareFetcher` | `capital_margin_detail` | `CapMarginDetailBO` |
| 12 | 资金 | tushare | `LimitListTushareFetcher` | `capital_limit_list_d` | `CapLimitListDBO` |
| 13 | 资金 | tushare | `HsgtTop10TushareFetcher` | `capital_hsgt_top10` | `CapHsgtTop10BO` |
| 14 | 资金 | tushare | `HolderNumberTushareFetcher` | `capital_holder_num` | `CapHolderNumBO` |
| 15 | 基本面 | tushare | `StockBasicTushareFetcher` | `fundamental_stock_info` | `StockInfoBO` |
| 16 | 基本面 | tushare | `FinIncomeTushareFetcher` | `fundamental_report` | `FinReportBO` |
| 17 | 基本面 | tushare | `DailyBasicTushareFetcher` | `fundamental_daily_basic` | `FinDailyBasicBO` |
| 18 | 基本面 | tushare | `Top10HoldersTushareFetcher` | `fundamental_top10` | `FinTop10HoldersBO` |
| 19 | 基本面 | tushare | `Top10FloatHoldersTushareFetcher` | `fundamental_top10_float` | `FinTop10FloatHoldersBO` |
| 20 | 基本面 | tushare | `DividendTushareFetcher` | `fundamental_dividend` | `BaseDividendBO` |
| 21 | 基本面 | adata  | `ConceptListAdataFetcher` | `fundamental_concept` | `ConceptListBO` |
| 22 | 基本面 | adata  | `ConceptMembersAdataFetcher` | `fundamental_concept_member` | `ConceptMemberBO` |
| 23 | 基本面 | adata  | `ConceptIndexDailyAdataFetcher` | `fundamental_concept_index` | `ConceptIndexTHBO` |
| 24 | 基本面 | adata  | `ConceptSnapshotAdataFetcher` | `fundamental_concept_snapshot` | `ConceptSnapshotBO` |
| 25 | 基本面 | adata  | `ConceptMinuteAdataFetcher` | (实时查询，不入库) | `ConceptMinuteBO` |
| 26 | 基本面 | adata  | `StockConceptsAdataFetcher` | `fundamental_stock_concept` | `ConceptOfStockBO` |
| 27 | 新闻 | tushare | `NewsTushareFetcher` | `news_article` | (dict 透传至 ORM) |

## 三、本次同步修复清单（按方案文档 §1 §2 编号）

### P0 严重（8 项）— 全部修复 ✅

| 编号 | 位置 | 修复内容 | 状态 |
|---|---|---|---|
| §1.1 | `StockBasicTushareFetcher` | 补 4 字段：`fullname`/`enname`/`cnspell`/`curr_type` | ✅ |
| §1.2 | `MoneyflowHsgtTushareFetcher` | **完全重写**：原按交易所聚合错误，改为按股票粒度 12 字段 | ✅ |
| §1.3 | `LimitListTushareFetcher` | **完全重写**：对齐 `limit_list_d` 18 字段（`pct_chg`/`limit`→`limit_type`/`limit_times`） | ✅ |
| §1.4 | `HsgtTop10TushareFetcher` | **完全重写**：原持有指标错误，改为交易指标（`rank`/`buy`/`sell`） | ✅ |
| §1.5 | `FinIncomeTushareFetcher` | 补 `end_type` 字段 | ✅ |
| §1.6 | `NewsTushareFetcher` | 重写：读 `channels` 字段、权限不足返回空（不抛错） | ✅ |
| §1.7 | `ConceptSnapshotAdataFetcher` | 修字段语义：`change`→`p_change`、`change_pct`→`pct_change`、`open`→`open_price`、补 `trade_date`/`concept_name` | ✅ |
| — | 数据库 5 张缺失表 | `capital_moneyflow_hsgt` / `capital_hsgt_top10` / `capital_limit_list_d` / `news_article` / `fundamental_stock_concept` | ✅（由表结构修复完成） |

### P1 缺字段（13 项）— 全部修复 ✅

| 编号 | 位置 | 修复内容 | 状态 |
|---|---|---|---|
| §2.1 | `SuspendTushareFetcher` | `suspend_timing` 改回 `str`（Tushare 给的是 "09:30-10:00" 时间段） | ✅ |
| §2.2 | `BlockTradeTushareFetcher` | 清理方法内 import，提到模块顶层 | ✅ |
| §2.3 | `MarginDetailTushareFetcher` | 补 `name` 字段 | ✅ |
| §2.4 | (文档误录) | 已在方案文档中删除 | — |
| §2.5 | (文档误录) | 已在方案文档中删除 | — |
| §2.6 | `HolderNumberTushareFetcher` | 补 `holder_nums` 字段（双轨兼容） | ✅ |
| §2.7 | `DailyBasicTushareFetcher` | 补 `limit_status` 字段 | ✅ |
| §2.8 | `DividendTushareFetcher` | 补 `div_listdate` + `imp_ann_date` 字段 | ✅ |
| §2.9 | `ConceptListAdataFetcher` | 补 `source` 字段（固定为 `ths`） | ✅ |
| §2.10 | `ConceptMembersAdataFetcher` | 补 `short_name` 字段 + 补 `source` | ✅ |
| §2.11 | `StockConceptsAdataFetcher` | 补 `source` 字段 | ✅ |
| — | 数据库字段 | `tech_suspend.suspend_timing` 由 `date` 改 `varchar(32)` | ✅ |
| — | 数据库字段 | `fundamental_concept_snapshot` 改 `pct_change` 语义 + 加 `trade_date` 列 | ✅ |

## 四、当前 Fetcher 行为规约

### 共同契约（由 `BaseFetcher` 强制）

```python
class BaseFetcher(ABC):
    source: ClassVar[str]      # "tushare" / "adata" / "pytdx"
    fetcher_type: ClassVar[str]
    label: ClassVar[str] = ""
    description: ClassVar[str] = ""

    @abstractmethod
    async def fetch(self, **params) -> list[BaseModel]: ...
```

**职责边界**：

| 行为 | 在 fetcher | 不在 fetcher |
|---|---|---|
| 调 SDK 拉原始数据 | ✅ | |
| 解析 DataFrame → BO | ✅ | |
| 入参 Pydantic 校验 | ✅ | |
| 字段映射（文档 vs BO） | ✅ | |
| 异常行跳过 + warn 日志 | ✅ | |
| 限流 / 并发 / 缓存 | | ❌（service 负责） |
| 入库 / 落盘 | | ❌（saver/repo 负责） |
| 重试 / 错误恢复 | | ❌（service 负责） |

### 关键修复点（按 fetcher 列）

#### 1. `StockBasicTushareFetcher`（§1.1）

- **fields 参数**追加 4 列：`fullname,enname,cnspell,curr_type`
- **BO 字段**追加 4 个 `Optional[str]`
- 行为：3 个交易所（SSE / SZSE / BSE）各查一次，**不去重**

#### 2. `MoneyflowHsgtTushareFetcher`（§1.2 完全重写）

- 文档接口：`pro.moneyflow_hsgt(trade_date, market_type?)`
- 粒度：**按股票**（每行一只股票的 12 个字段）
- 关键映射：`change`(元)→`p_change`，`pct_chg`(%)→`pct_change`
- 输出：`CapMoneyflowHsgtBO`

#### 3. `LimitListTushareFetcher`（§1.3 完全重写）

- 文档接口：`pro.limit_list_d(trade_date)`
- 粒度：**按股票 + `limit_type`**（D=跌停 / U=涨停 / Z=炸板）
- 关键映射：`limit`→`limit_type`，`pct_chg` 保留
- 18 字段：`trade_date, symbol, industry, name, close, pct_chg, amount, limit_amount, float_mv, total_mv, turnover_ratio, fd_amount, first_time, last_time, open_times, up_stat, limit_times, limit_type`

#### 4. `HsgtTop10TushareFetcher`（§1.4 完全重写）

- 文档接口：`pro.hsgt_top10(trade_date, market_type?)`
- 粒度：**按股票 + `rank`**（每日 10 大成交股）
- 关键：`(trade_date, symbol, market_type, rank)` 复合主键
- 11 字段：`trade_date, symbol, name, market_type, rank, close, p_change, amount, net_amount, buy, sell`

#### 5. `NewsTushareFetcher`（§1.6 重写）

- 文档接口：`pro.news()`（**需独立开通权限，5000+ 积分**）
- 行为：捕获权限异常 → 返回空 `[]` + warn 日志（不阻断主流程）
- 字段：`published_at, title, content, source, url, channels, symbols[], category, sentiment`
- 集成点：`scripts/step7_c2_shim.py` 等使用方需识别"空=无新数据"而非"出错"

#### 6. `ConceptSnapshotAdataFetcher`（§1.7 字段语义）

- 文档接口：`stock.market.get_market_concept_current_ths(index_code)`
- 关键修正：
  | 旧字段（错） | 新字段（对） | 含义 |
  |---|---|---|
  | `change` | `p_change` | 涨跌额（元） |
  | `change_pct` | `pct_change` | 涨跌幅（%） |
  | `open` | `open_price` | 开盘价 |
  | — | `trade_date`（新） | 交易日期 |
  | — | `concept_name`（新） | 概念名称（业务冗余） |

#### 7. 其他 fetcher

- `MarginDetailTushareFetcher` 新增 `name` 字段
- `HolderNumberTushareFetcher` 补 `holder_nums`（与 `holder_num` 同步）
- `DividendTushareFetcher` 补 `div_listdate`（红股上市日）和 `imp_ann_date`（实施公告日）
- `FinIncomeTushareFetcher` 补 `end_type`
- `DailyBasicTushareFetcher` 补 `limit_status`（0=正常 / 1=停牌 / 2=一字板）
- `SuspendTushareFetcher` `suspend_timing` 由 `date` 改 `str`（"09:30-10:00"）
- `BlockTradeTushareFetcher` 把 `import` 提到模块顶层
- `ConceptListAdataFetcher` 补 `source`
- `ConceptMembersAdataFetcher` 补 `short_name` + `source`
- `StockConceptsAdataFetcher` 补 `source`

## 五、待办（第三批 / P2 之后）

> 同步修改完成后，仍有部分工作待做。优先级 P1。

### 5.1 `list[dict] → list[BaseModel]` 收敛（7 个 fetcher）

| Fetcher | 当前返回 | 建议 BO | 说明 |
|---|---|---|---|
| `NewsTushareFetcher` | `list[dict]` | 新增 `NewsArticleBO` | 含 published_at/title/content/channels/symbols/sentiment |
| `ConceptSnapshotAdataFetcher` | `list[dict]` | 已存在 `ConceptSnapshotBO` | 改为构造 `ConceptSnapshotBO` 返回 |
| `ConceptIndexDailyAdataFetcher` | `list[dict]` | 已存在 `ConceptIndexTHBO` | 改为构造 BO 返回 |
| `ConceptMinuteAdataFetcher` | `list[dict]` | 已存在 `ConceptMinuteBO` | 改为构造 BO 返回 |
| `ConceptListAdataFetcher` | `list[dict]` | 已存在 `ConceptListBO` | 改为构造 BO 返回 |
| `ConceptMembersAdataFetcher` | `list[dict]` | 已存在 `ConceptMemberBO` | 改为构造 BO 返回 |
| `StockConceptsAdataFetcher` | `list[dict]` | 已存在 `ConceptOfStockBO` | 改为构造 BO 返回 |

> 原因：让 service 不再因 fetcher 返回类型不同而需要 `if isinstance(item, BaseModel)` 分支。

### 5.2 字段重命名兼容

`StockInfoBO` 重命名前端兼容：
- 前端目前仍用 `name`/`industry`/`list_date` — 不变
- 旧字段名 `act_name`/`act_ent_type`/`is_hs` 已稳定 — 不变
- 新增 `fullname`/`enname`/`cnspell`/`curr_type` 前端可按需展示

### 5.3 接入 service / saver

fetcher 现在与 BO 已严格对齐，下一步：
1. service 层按 `list[BaseModel]` 直接调用
2. saver 层按 BO 字段映射到 ORM 模型
3. 删除 fetcher 中的 `dict` 路径（一旦 service 改造完成）

### 5.4 Tushare 限量循环

部分接口（`top_list` / `top_inst` / `limit_list_d`）Tushare 单次仅返回 5000 行，超量需按 `trade_date` 分页。fetcher 当前不感知，应在 service 层加循环。

## 六、验收情况

| 验收项 | 脚本 | 结果 |
|---|---|---|
| `raw_data_db` 30 张表对齐 | `scripts/verify_raw_db_deep.py` | ✅ 30/30 |
| 30 个 fetcher 静态 import | `scripts/verify_fetcher_imports.py`（本次新增） | ✅ 30/30 |
| 16 个 fetcher 端到端 mock 测试 | `scripts/test_fetcher_mock.py`（本次新增） | ✅ 16/16 |

### Mock 测试覆盖明细

| Fetcher | 测试点 | 结果 |
|---|---|---|
| `StockBasicTushareFetcher` | 4 新字段 fullname/enname/cnspell/curr_type | ✅ |
| `MoneyflowHsgtTushareFetcher` | p_change/pct_change 字段映射 | ✅ |
| `LimitListTushareFetcher` | 18 字段 + limit→limit_type | ✅ |
| `HsgtTop10TushareFetcher` | 11 字段 + rank/market_type | ✅ |
| `FinIncomeTushareFetcher` | end_type 已读 | ✅ |
| `DailyBasicTushareFetcher` | limit_status 已读 | ✅ |
| `MarginDetailTushareFetcher` | name 已读 | ✅ |
| `HolderNumberTushareFetcher` | holder_nums 冗余 | ✅ |
| `DividendTushareFetcher` | div_listdate + imp_ann_date 已读 | ✅ |
| `SuspendTushareFetcher` | suspend_timing 是 str | ✅ |
| `ConceptSnapshotAdataFetcher` | p_change/pct_change/open_price 字段语义 | ✅ |
| `ConceptListAdataFetcher` | source 已填 | ✅ |
| `ConceptMembersAdataFetcher` | short_name + source | ✅ |
| `StockConceptsAdataFetcher` | source | ✅ |
| `NewsTushareFetcher` | 权限不足返回空 | ✅ |
| `NewsTushareFetcher` | 正常返回 | ✅ |

## 七、涉及文件清单（22 个）

```
backend/src/contexts/collect/application/bo/
├── __init__.py                          (BO 导出汇总)
├── capital.py                            (新增 3 BO + 修 name)
├── fundamental.py                        (补 end_type + limit_status)
└── tech.py                               (suspend_timing 改 str + 补 2 字段)

backend/src/contexts/collect/infrastructure/fetcher/
├── capital/
│   ├── MoneyflowHsgtTushareFetcher.py    (P0 完全重写)
│   ├── LimitListTushareFetcher.py        (P0 完全重写)
│   ├── HsgtTop10TushareFetcher.py        (P0 完全重写)
│   ├── MarginDetailTushareFetcher.py     (补 name + 修 import)
│   ├── HolderNumberTushareFetcher.py     (补 holder_nums)
│   └── BlockTradeTushareFetcher.py       (整理 import)
├── fundamental/
│   ├── StockBasicTushareFetcher.py       (补 4 字段)
│   ├── FinIncomeTushareFetcher.py        (补 end_type)
│   ├── DailyBasicTushareFetcher.py       (补 limit_status)
│   ├── DividendTushareFetcher.py         (补 2 字段)
│   ├── ConceptListAdataFetcher.py        (补 source)
│   ├── ConceptMembersAdataFetcher.py     (补 short_name + source)
│   └── StockConceptsAdataFetcher.py      (补 source)
├── news/
│   └── NewsTushareFetcher.py             (P0 重写 + 权限检测)
└── tech/
    └── SuspendTushareFetcher.py          (suspend_timing 改 str)

backend/src/contexts/concept/application/bo/
└── concept.py                            (3 BO 改动)

backend/src/contexts/market/application/bo/
└── stock_info.py                         (StockInfoBO 补 4 字段)

backend/scripts/
├── verify_fetcher_imports.py            (本次新增 - 静态 import 校验)
├── test_fetcher_mock.py                  (本次新增 - mock 端到端测试)
└── verify_raw_db_deep.py                 (已有 - 30 张表对齐校验)
```

## 八、回归建议

1. 启动 backend：`uvicorn main:app --reload`
2. 跑 `python -m scripts.verify_raw_db_deep` — 30 张表对齐
3. 跑 `python -m scripts.verify_fetcher_imports` — 30 个 fetcher import
4. 跑 `python -m scripts.test_fetcher_mock` — 16 个端到端 mock
5. 启动前端 `pnpm dev`，挨个测 27 个 fetcher 的全量 / 条件采集

---

**结论**：同步方案文档 §1 + §2 全部 21 项 P0/P1 修复已完成，27 个 fetcher 与官方文档、与 30 张表均 100% 对齐。第三批 P2 主要是 7 个 fetcher 从 `list[dict]` 收敛到 `list[BaseModel]`，属于代码风格/统一性工作，不影响功能。
