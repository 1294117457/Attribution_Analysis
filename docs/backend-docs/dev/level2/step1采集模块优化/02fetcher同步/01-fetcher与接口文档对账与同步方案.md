# fetcher 与接口文档对账 — 同步方案

> 目标：对照 `docs/backend-docs/data/{tushare,adata,pytdx}.md` 三份接口文档，逐一核对 `backend/src/contexts/collect/infrastructure/fetcher/` 下 27 个 fetcher 的：
> 1. **接口名**是否正确
> 2. **调用参数**是否对齐文档
> 3. **输出字段**是否覆盖文档全部字段
> 4. **返回类型**（BO/PO 字段）是否与新表（见 [02-raw_data表清单](../02-raw_data表清单.md)）匹配
> 5. **基础行为**（缓存、限流、批大小、调用频次）是否符合接口文档的"限量/积分"约束
>
> **本轮只输出方案**，不修改任何 fetcher 代码。

---

## 0. fetcher 总览

| # | fetcher | 接口 | 文档来源 | 物理表 | 状态 |
|---|---|---|---|---|---|
| 1 | DailyKlineTushareFetcher | `pro.daily` | tushare.md | tech_kline_daily | ✅ OK |
| 2 | AdjFactorTushareFetcher | `pro.adj_factor` | tushare.md | tech_adj_factor | ✅ OK |
| 3 | SuspendTushareFetcher | `pro.suspend_d` | tushare.md | tech_suspend | ⚠️ 1 处 |
| 4 | NameChangeTushareFetcher | `pro.namechange` | tushare.md | tech_name_change | ✅ OK |
| 5 | MinuteKlinePytdxFetcher | `api.get_security_bars` | pytdx.md | 不入库 | ✅ OK |
| 6 | StockBasicTushareFetcher | `pro.stock_basic` | tushare.md | fundamental_stock_info | 🔴 3 处 |
| 7 | MoneyflowTushareFetcher | `pro.moneyflow` | tushare.md | capital_moneyflow | ✅ OK |
| 8 | MoneyflowHsgtTushareFetcher | `pro.moneyflow_hsgt` | tushare.md | capital_moneyflow_hsgt | 🔴 4 处 |
| 9 | TopListTushareFetcher | `pro.top_list` | tushare.md | capital_top_list | ✅ OK |
| 10 | TopInstTushareFetcher | `pro.top_inst` | tushare.md | capital_top_inst | ✅ OK |
| 11 | BlockTradeTushareFetcher | `pro.block_trade` | tushare.md | capital_block_trade | ⚠️ 1 处 |
| 12 | MarginDetailTushareFetcher | `pro.margin_detail` | tushare.md | capital_margin_detail | ⚠️ 1 处 |
| 13 | LimitListTushareFetcher | `pro.limit_list_d` | tushare.md | capital_limit_list_d | 🔴 5 处 |
| 14 | HsgtTop10TushareFetcher | `pro.hsgt_top10` | tushare.md | capital_hsgt_top10 | 🔴 4 处 |
| 15 | HolderNumberTushareFetcher | `pro.stk_holdernumber` | tushare.md | capital_holder_num | ⚠️ 1 处 |
| 16 | FinIncomeTushareFetcher | `pro.income` | tushare.md | fundamental_report | 🔴 1 处 |
| 17 | DailyBasicTushareFetcher | `pro.daily_basic` | tushare.md | fundamental_daily_basic | ⚠️ 1 处 |
| 18 | Top10HoldersTushareFetcher | `pro.top10_holders` | tushare.md | fundamental_top10 | ✅ OK |
| 19 | Top10FloatHoldersTushareFetcher | `pro.top10_floatholders` | tushare.md | fundamental_top10_float | ✅ OK |
| 20 | DividendTushareFetcher | `pro.dividend` | tushare.md | fundamental_dividend | ⚠️ 3 处 |
| 21 | NewsTushareFetcher | `pro.news` | tushare.md | news_article | 🔴 5 处 |
| 22 | ConceptListAdataFetcher | `stock.info.all_concept_code_ths` | adata.md | fundamental_concept | ⚠️ 1 处 |
| 23 | ConceptMembersAdataFetcher | `stock.info.concept_constituent_ths` | adata.md | fundamental_concept_member | ⚠️ 2 处 |
| 24 | ConceptIndexDailyAdataFetcher | `stock.market.get_market_concept_ths` | adata.md | fundamental_concept_index | ✅ OK |
| 25 | ConceptSnapshotAdataFetcher | `stock.market.get_market_concept_current_ths` | adata.md | fundamental_concept_snapshot | 🔴 3 处 |
| 26 | ConceptMinuteAdataFetcher | `stock.market.get_market_concept_min_ths` | adata.md | 不入库 | ✅ OK |
| 27 | StockConceptsAdataFetcher | `stock.info.get_concept_ths` | adata.md | fundamental_stock_concept | ⚠️ 2 处 |

**统计**：✅ 14 / ⚠️ 13 / 🔴 8（27 个 fetcher 中 21 个需要改动）

---

## 1. P0 严重不一致（8 处，fetcher 与表/文档全维度冲突）

> 含义：fetcher 返回的字段、表结构、文档接口字段**三方不匹配**——若不修，**入库即报错**或**数据完全错误**。

### 1.1 StockBasicTushareFetcher 🔴

**接口**：`pro.stock_basic` (Tushare)
**目标表**：`fundamental_stock_info`（已补 4 字段：fullname / enname / cnspell / curr_type）

**3 处问题**：

| # | 问题 | 当前 | 应为 | 修复方案 |
|---|---|---|---|---|
| 1 | `_STOCK_BASIC_FIELDS` 缺字段 | `ts_code,symbol,name,area,industry,market,exchange,list_date,delist_date,list_status,is_hs,act_name,act_ent_type`（13）| 文档列出 16 字段：`+fullname,enname,cnspell,curr_type` | 拼接这 4 个字段名 |
| 2 | fetcher 没映射新字段 | BO 构造里无 `fullname` 等 | 需补 4 行 | 仿照 `name=text(r, "name")` 模式 |
| 3 | `StockInfoBO` 缺字段 | 21 列（已含 4 新列）| ✅ OK | 已修复 |

**修复要点**（仅文档，**不写代码**）：

```
1. StockBasicTushareFetcher.py:
   - 把 _STOCK_BASIC_FIELDS 末尾追加 ",fullname,enname,cnspell,curr_type"
   - 在 StockInfoBO(...) 构造里加 4 行：
       fullname=text(r, "fullname"),
       enname=text(r, "enname"),
       cnspell=text(r, "cnspell"),
       curr_type=text(r, "curr_type"),

2. StockInfoBO（market/application/bo/stock_info.py）：
   - 确认有 4 个新字段（已修复，见 02 修复记录）
   - 若没有，补 4 个 Mapped[str|None] 字段
```

---

### 1.2 MoneyflowHsgtTushareFetcher 🔴

**接口**：`pro.moneyflow_hsgt` (Tushare, 2000 积分)
**目标表**：`capital_moneyflow_hsgt`（16 列，**已建好**）

**4 处问题**：

| # | 问题 | 当前 | 应为 |
|---|---|---|---|
| 1 | 数据粒度错位 | fetcher 按"交易所" (SH/SZ/HK) 聚合（`buy_amount`/`sell_amount`）| 文档：按"**单只股票**"返回（`ts_code`/`name`/`close`/`change`/`rank`）|
| 2 | 缺字段 | 7 字段 | 文档 12 字段：`+symbol,name,close,change(p_change),pct_change,rank,amount,net_amount,buy,sell` |
| 3 | `exchange` 字段 | 用 `exchange` 字符串 | 文档用 `market_type` 字段（`1`=沪市 / `3`=深市），表里也叫 `market_type` |
| 4 | 返回 dict 的字段 | 用 `exchange` / `buy_amount` / `sell_amount` | 改为表字段 `market_type` / `buy` / `sell` / `p_change` 等 |

**修复要点**：

```
1. fetcher 解析逻辑改写：
   - 不再读 exchange/buy_amount/sell_amount
   - 改读 ts_code/name/close/change(p_change)/pct_change/rank/amount/net_amount/buy/sell/market_type
   - 字段映射：
       ts_code[:6]  -> symbol
       change       -> p_change
       market_type  -> market_type

2. UK (trade_date, symbol, market_type) 与新表对齐
```

**测试方式**：用 `pro.moneyflow_hsgt(trade_date=20251017)` 拉一次看实际返回，确认字段。

---

### 1.3 LimitListTushareFetcher 🔴

**接口**：`pro.limit_list_d` (Tushare, 5000 积分)
**目标表**：`capital_limit_list_d`（22 列，**已建好**）

**5 处问题**：

| # | 问题 | 当前 | 应为 |
|---|---|---|---|
| 1 | 缺字段 | 9 字段 | 文档 19 字段：`+industry,pct_chg,limit_amount,float_mv,total_mv,turnover_ratio,fd_amount,first_time,last_time,open_times,up_stat,limit_times,limit_type` |
| 2 | 列名错位 | `pct_change` 字段读自文档 `pct_change` | 文档实际叫 `pct_chg`（fetch error: `KeyError: pct_change`）|
| 3 | 列名错位 | 拼 `close_price` | 文档 `close` |
| 4 | `limit_type` 推断错 | 用 `pct > 0` 推断 "up_limit"/"down_limit" | 文档直接给 `limit` 字段（D=跌停/U=涨停/Z=炸板），**必须用原字段**而非推断 |
| 5 | `board_count` 错 | 读 `board_count` | 文档实际叫 `limit_times`（连板数）|
| 6 | 缺 `name` 字段 | 没读 `name` | 文档有 `name` 字段 |
| 7 | 缺 `industry` 字段 | 没读 `industry` | 文档有 |
| 8 | `reason` 误用 | fetcher 读 `reason` | limit_list_d 文档**没有** reason 字段（这是 top_list 的字段）|
| 9 | `first_limit_time` 错 | 读 `first_limit_time` | 文档叫 `first_time` |

**字段映射修正表**：

| 旧（fetcher 错误读）| 新（按文档）|
|---|---|
| `pct_change` | `pct_chg` |
| `close` (用 close_price) | `close` |
| `limit` (推断) | `limit`（**直接读，不推断**）|
| `board_count` | `limit_times` |
| `first_limit_time` | `first_time` |
| `last_time` | 文档同 `last_time` ✅ |
| `board_strength` | **文档无此字段，删除** |
| `reason` | **文档无此字段，删除** |
| `pct_chg` (改名) | 用 `pct_chg` |

**修复要点**：

```
1. fetcher _parse 全部重写，按文档 19 字段一一对应：
   trade_date, ts_code -> symbol, name, industry, close, pct_chg,
   amount, limit_amount, float_mv, total_mv, turnover_ratio,
   fd_amount, first_time, last_time, open_times, up_stat,
   limit_times, limit (改名 limit_type)

2. 删除 board_strength / reason 字段（文档无）

3. limit_type 改为直接读 limit 字段
```

---

### 1.4 HsgtTop10TushareFetcher 🔴

**接口**：`pro.hsgt_top10` (Tushare)
**目标表**：`capital_hsgt_top10`（15 列，**已建好**）

**4 处问题**：

| # | 问题 | 当前 | 应为 |
|---|---|---|---|
| 1 | 数据语义错位 | fetcher 是"持仓"视角（`holding_days`/`share_ratio`/`hold_amount`）| 文档是"每日成交"视角（`name`/`close`/`change`/`rank`/`amount`/`net_amount`/`buy`/`sell`）|
| 2 | 字段全部错 | 6 字段（基于"持仓"语义）| 文档 11 字段：`+name,close,change(p_change),rank,market_type,amount,net_amount,buy,sell` |
| 3 | `ts_code` → symbol | ✅ OK | ✅ |
| 4 | 缺 `market_type` 字段 | 没读 | 文档有 |

**字段映射修正**：

| 旧（fetcher 错）| 新（按文档）|
|---|---|
| `holding_days` | **删除**（文档无）|
| `share_ratio` | **删除**（文档无）|
| `hold_amount` | **删除**（文档无）|
| `net_amount` | `net_amount` ✅ |
| （缺）| `name` |
| （缺）| `close` |
| （缺）| `change`（改名 p_change）|
| （缺）| `rank` |
| （缺）| `market_type` |
| （缺）| `amount` |
| （缺）| `buy` |
| （缺）| `sell` |

**修复要点**：完全重写 `_parse` 按文档 11 字段。

---

### 1.5 FinIncomeTushareFetcher 🔴

**接口**：`pro.income` (Tushare, 2000 积分)
**目标表**：`fundamental_report`（24 列，**已补 end_type**）

**1 处问题**：

| # | 问题 | 当前 | 应为 |
|---|---|---|---|
| 1 | 缺 `end_type` | BO 构造里无 | 文档有 `end_type` 字段 |

**修复要点**：

```
在 FinReportBO(...) 构造里加一行：
    end_type=text(r, "end_type"),
```

> 注：本 fetcher 整体可考虑后续 PR 重写（拆为 income/balance/cashflow 三表），但**当前 P0 只修 end_type 一处**。

---

### 1.6 NewsTushareFetcher 🔴

**接口**：`pro.news` (Tushare, **需单独开通权限**)
**目标表**：`news_article`（13 列，**已建好**）

**5 处问题**：

| # | 问题 | 当前 | 应为 |
|---|---|---|---|
| 1 | 取 `ts_codes` 字段错 | 读 `row["ts_codes"]`（行内 _parse_symbols）| 文档叫 `channels`（频道列表），**`ts_codes` 不是接口字段**|
| 2 | 缺 `symbols` 字段填值 | 没正确填入 | 应读 `ts_codes`（如有）或留空（待 AI 分类）|
| 3 | `_infer_category` 启发式 | 用关键词匹配 利好/利空/中性 | ⚠️ 可保留作为兜底，但**应注明"占位 AI 分类"** |
| 4 | 返回 dict 字段不匹配表 | `published_at` / `title` / `content` / `source` / `url` | ✅ 基本对应，但 `symbols` 字段类型应从 `list[str]` 改为 `list[str]|None` |
| 5 | 文档没给的字段塞进表 | 当前 fetcher 不写 | 表已有 `sentiment` / `category` / `symbols` 列，**fetcher 必须有相应逻辑填**（哪怕为空）|

**修复要点**：

```
1. _parse 字段读取：
   - 文档返回: datetime, content, title, channels
   - 改读 row["datetime"] -> published_at
   - 改读 row["channels"] -> channels (或入表，类型 text/str)
   - 保留 _infer_category 启发式（写入 category 列）
   - symbols 列表（来自 channels 的关联股票）保留 _parse_symbols 逻辑
   - 加 sentiment 字段默认为空

2. URL / source / title / content 直接读
```

> ⚠️ **注**：`pro.news` 在 Tushare 是**高权限接口**，需单独申请。当前 fetcher 实际**跑不通**（返回空），**建议本 PR 也暂缓**——先把 P0/P1 字段改对，Tushare 权限开通过后再调通。

---

### 1.7 ConceptSnapshotAdataFetcher 🔴

**接口**：`stock.market.get_market_concept_current_ths` (Adata)
**目标表**：`fundamental_concept_snapshot`（21 列，**已修字段语义**）

**3 处问题**：

| # | 问题 | 当前 | 应为 |
|---|---|---|---|
| 1 | 字段语义错位 | `change` → 装 `change` 字段（**但表里改名为 p_change**）| 文档 `change`（涨跌额）→ 表 `p_change`（已修）|
| 2 | 缺 `trade_date` | 没读 | 文档有 `trade_date` |
| 3 | 缺 `concept_name` 字段 | 没读 | 文档没有但**业务需要**（redis/前端用）|
| 4 | 缺 `captured_at` 字段 | 没设 | 表要求 `captured_at` 自动填 |

**修复要点**：

```
1. _parse 增加：
   - trade_date 读 row.get("trade_date")
   - concept_name 读 row.get("name") 或 service 层补
   - 把 dict 字段名 change -> p_change, change_pct -> pct_change（对齐表）
   - 写库时 captured_at 用数据库 now()

2. 删掉或重命名 key：
   - "change" -> "p_change"
   - "change_pct" -> "pct_change"
   - "open" -> "open_price"（表里叫 open_price）
```

---

### 1.8 StockBasicTushareFetcher（同 1.1）

（已列 1.1）

---

## 2. P1 字段缺失（13 处，fetcher 缺 1~3 个文档字段）

> 含义：fetcher 整体能用，但漏了几个文档明确列出的字段——补上后数据更完整。

### 2.1 SuspendTushareFetcher ⚠️

| 缺字段 | 文档位置 | 修复 |
|---|---|---|
| `suspend_timing` | 文档说"日内停牌时间段（字符串如 09:30-10:00）" | 字段已写但**用 `parse_list_date` 错误**（当成 date 解析）|

**修复**：

```
fetcher 第 38 行:
  suspend_timing=parse_list_date(r.get("suspend_timing")),   # ❌ 错，suspend_timing 是字符串
改:
  suspend_timing=str(r.get("suspend_timing")) or None,        # ✅ 原样存
```

> 这正好对应表结构 §2.1 修复（`suspend_timing: date → varchar(32)`）

---

### 2.2 BlockTradeTushareFetcher ⚠️

| 缺字段 | 修复 |
|---|---|
| `name`（股票名）| fetcher 第 45 行已读 `name=text(r, "name")` ✅ |

**1 处小问题**：

```
fetcher 函数内部 import pydantic：
  from pydantic import BaseModel as _BM, ConfigDict
应改为文件顶部 import（与同类 fetcher 一致）
```

---

### 2.3 MarginDetailTushareFetcher ⚠️

| 缺字段 | 修复 |
|---|---|
| `name`（表已补）| fetcher 没读 |

**修复**：

```
在 CapMarginDetailBO(...) 构造里加：
  name=text(r, "name"),
```

---

### 2.4 LimitListTushareFetcher（同 1.3）

（已列 1.3）

---

### 2.5 HsgtTop10TushareFetcher（同 1.4）

（已列 1.4）

---

### 2.6 HolderNumberTushareFetcher ⚠️

| 缺字段 | 修复 |
|---|---|
| `holder_nums` | 表里有但 fetcher 没写 |

**修复**：

```
在 CapHolderNumBO(...) 构造里加：
  holder_nums=float(num(r, "holder_num") or 0) if num(r, "holder_num") else None,
# 解释：表 holder_nums 是 double precision 类型冗余字段（业务暂未使用，存与 holder_num 同值）
```

---

### 2.7 DailyBasicTushareFetcher ⚠️

| 缺字段 | 修复 |
|---|---|
| `limit_status`（表已补）| fetcher 没读 |

**修复**：

```
在 FinDailyBasicBO(...) 构造里加：
  limit_status=int(num(r, "limit_status") or 0) if num(r, "limit_status") is not None else None,
```

---

### 2.8 DividendTushareFetcher ⚠️

| 缺字段 | 修复 |
|---|---|
| `div_listdate` | 文档有（"红股上市日"）|
| `imp_ann_date` | 文档有（"实施公告日"）|
| `base_date` | 文档 "N"（不默认显示），**不补** |
| `base_share` | 文档 "N"，**不补** |

**修复**：

```
在 BaseDividendBO(...) 构造里加 2 行：
  div_listdate=parse_list_date(r.get("div_listdate")),
  imp_ann_date=parse_list_date(r.get("imp_ann_date")),
```

> 表里 §4.5 已加这 2 列。

---

### 2.9 ConceptListAdataFetcher ⚠️

| 缺字段 | 修复 |
|---|---|
| `source` 字段没读 | fetcher 没读 source |

**修复**：

```
在 _parse 加：
  "source": _str(row.get("source")) or "ths",
```

---

### 2.10 ConceptMembersAdataFetcher ⚠️

| 缺字段 | 修复 |
|---|---|
| `short_name`（表已补）| fetcher 没读 |
| `reason` | 文档有 `concept_constituent_ths` 没这个字段——**别误加** |

**修复**：

```
items.append({
    "index_code": index_code,
    "symbol": sym,
    "short_name": _str(row.get("short_name")),  # 补
    "reason": None,  # 该接口没此字段
})
```

> `_str` 在 `ConceptListAdataFetcher` 里 import 即可。

---

### 2.11 StockConceptsAdataFetcher ⚠️

| 缺字段 | 修复 |
|---|---|
| `concept_id` 字段 | 表用 `concept_id`（int），fetcher 写 `index_code` (str) |
| `source` 字段 | fetcher 没写 |

**修复**：

```
items.append({
    "symbol": symbol,
    "concept_id": int(index_code) if index_code.isdigit() else None,  # 调整
    "index_code": index_code,                                          # 冗余保留便于调试
    "name": name,
    "source": "ths",                                                   # 补
    "reason": _str(row.get("reason")),
})
```

> **重点**：写入 `fundamental_stock_concept` 表时需要 `concept_id`（int，外键到 `fundamental_concept.id`）而非字符串 `index_code`。这是**数据语义**的差异——需 service 层做 `index_code → concept_id` 映射。

---

### 2.12 BlockTradeTushareFetcher（同 2.2）

（已列 2.2）

---

### 2.13 MoneyflowHsgtTushareFetcher（同 1.2）

（已列 1.2）

---

## 3. P2 基础行为问题（隐性问题，不改字段但要改逻辑）

### 3.1 接口调用参数不全

> 含义：fetcher 没把文档允许的**入参**全部暴露，导致按需查询时做不到精细化。

| fetcher | 文档可传入参 | 当前传入参 | 缺失入参 |
|---|---|---|---|
| MoneyflowTushareFetcher | `ts_code` / `trade_date` / `start_date` / `end_date` | `trade_date` only | `start_date` / `end_date` / `ts_code` |
| TopListTushareFetcher | `trade_date` (Y) / `ts_code` (N) | `trade_date` only | `ts_code` |
| TopInstTushareFetcher | `trade_date` (Y) / `ts_code` (N) | `trade_date` only | `ts_code` |
| MarginDetailTushareFetcher | `ts_code` / `trade_date` / `start_date` / `end_date` | `trade_date` only | `ts_code` / `start_date` / `end_date` |
| DailyBasicTushareFetcher | `ts_code` (Y) / `trade_date` (N) / `start_date` / `end_date` | `trade_date` only | `ts_code` / `start_date` / `end_date` |
| HolderNumberTushareFetcher | `ts_code` / `ann_date` / `enddate` / `start_date` / `end_date` | `ts_code` only | `ann_date` / `enddate` |
| StockBasicTushareFetcher | `ts_code` / `name` / `market` / `list_status` / `exchange` / `is_hs` | `exchange` + `list_status` | `ts_code` / `name` / `market` / `is_hs` |
| AdjFactorTushareFetcher | `ts_code` / `trade_date` / `start_date` / `end_date` | `ts_code` only | `trade_date` / `start_date` / `end_date` |
| BlockTradeTushareFetcher | `ts_code` / `trade_date` / `start_date` / `end_date` | `trade_date` only | `ts_code` / `start_date` / `end_date` |
| SuspendTushareFetcher | `ts_code` / `trade_date` / `start_date` / `end_date` / `suspend_type` | `trade_date` only | `ts_code` / `suspend_type` / `start_date` / `end_date` |
| NameChangeTushareFetcher | `ts_code` / `start_date` / `end_date` | 无（拉全量） | 全部 |
| Top10HoldersTushareFetcher | `ts_code` (Y) / `period` / `ann_date` / `start_date` / `end_date` | `ts_code` only | `period` / `ann_date` |
| Top10FloatHoldersTushareFetcher | `ts_code` (Y) / `period` / `ann_date` / `start_date` / `end_date` | `ts_code` only | `period` / `ann_date` |
| FinIncomeTushareFetcher | `ts_code` (Y) / `ann_date` / `f_ann_date` / `start_date` / `end_date` / `period` / `report_type` / `comp_type` | `ts_code` only | `ann_date` / `period` / `report_type` / `comp_type` |
| DividendTushareFetcher | `ts_code` / `ann_date` / `record_date` / `ex_date` / `imp_ann_date` | 无（拉全量）| 全部 |
| MoneyflowHsgtTushareFetcher | `trade_date` / `start_date` / `end_date` / `market_type` | `trade_date` only | `start_date` / `end_date` / `market_type` |
| HsgtTop10TushareFetcher | `ts_code` / `trade_date` / `start_date` / `end_date` / `market_type` | `trade_date` only | `market_type`（最常用）|
| LimitListTushareFetcher | `trade_date` / `ts_code` / `limit_type` / `exchange` / `start_date` / `end_date` | `trade_date` only | `limit_type` / `exchange` |

**修复原则**：**不影响**当前批量采集场景，本 PR 不改（属于优化项）。

### 3.2 限量 / 积分约束

| fetcher | 文档限量 | 当前 fetcher 行为 | 是否超限？ |
|---|---|---|---|
| AdjFactorTushareFetcher | 2000 积分 / 5000+ 高频 | 直接调 | ✅ OK |
| MarginDetailTushareFetcher | 2000 积分起 | 直接调 | ✅ OK |
| HsgtTop10TushareFetcher | 2000 积分起 | 直接调 | ✅ OK |
| TopInstTushareFetcher | **5000 积分起** | 直接调 | ⚠️ 需确认 Tushare 账号 ≥ 5000 积分 |
| LimitListTushareFetcher | **5000 积分 / 8000 积分** | 直接调 | ⚠️ 需确认 Tushare 账号 ≥ 5000 积分 |
| FinIncomeTushareFetcher | 2000 / **income_vip 5000** | 直接调 income | ✅ OK（用普通版）|
| MoneyflowTushareFetcher | 2000 | 直接调 | ✅ OK |
| MoneyflowHsgtTushareFetcher | 2000 | 直接调 | ✅ OK |
| NewsTushareFetcher | **需单独开通权限** | 直接调 | 🔴 当前**调不通** |

**修复**：
- NewsTushareFetcher：增加**接口未开通检测**，捕获 `tushare` 抛出的权限错误，**不写入 DB**，仅在日志告警
- TopInst / LimitList：在 fetcher 顶部加注释，注明最低积分要求

### 3.3 批大小 / 单次限量

| fetcher | 文档限量 | 当前 fetcher |
|---|---|---|
| daily_kline (单股) | 单次返回 ~6000 行 | `_BATCH=800`（单股）✅ |
| daily_basic (全市场) | 单次 6000 | 直接调（一次 5000+ 全 A 股）⚠️ 边界 |
| top_list | 单次 10000 | 直接调 ✅ |
| top_inst | 单次 10000 | 直接调 ✅ |
| block_trade | 单次 1000 | 直接调 ✅ |
| limit_list_d | 单次 2500 | 直接调 ✅ |
| margin_detail | 单次 6000 | 直接调 ✅ |
| holder_num | 单次 3000 | 直接调 ✅ |

**结论**：均在文档限量内，**本 PR 不改**。后续 PR 加循环批量拉取。

---

## 4. P3 已有/可保留的"非标准"返回（list[dict]）

> 含义：这 3 个 fetcher（MoneyflowHsgt / LimitList / HsgtTop10 / News / ConceptSnapshot / ConceptMinute / StockConcepts）返回 `list[dict]` 而非 `list[BaseModel]`，**与 base.py 抽象的 `list[BaseModel]` 注释冲突**。

| fetcher | 当前返回类型 | 是否需要改为 BO |
|---|---|---|
| MoneyflowHsgtTushareFetcher | list[dict] | ✅ 需要（统一架构）|
| LimitListTushareFetcher | list[dict] | ✅ 需要 |
| HsgtTop10TushareFetcher | list[dict] | ✅ 需要 |
| NewsTushareFetcher | list[dict] | ✅ 需要 |
| ConceptSnapshotAdataFetcher | list[dict] | ✅ 需要 |
| ConceptMinuteAdataFetcher | list[dict] | ✅ 需要（实时查询） |
| StockConceptsAdataFetcher | list[dict] | ✅ 需要 |

**建议**：本 PR 不强求（**P0 完成后另起 PR**），先把字段对齐、字段映射改对。

---

## 5. 修复优先级（建议执行顺序）

```
┌─────────────────────────────────────────────────────────────┐
│ 第一批：P0 严重（必须修，3 个 PR 内）                        │
│   1. MoneyflowHsgtTushareFetcher (1.2) — 字段语义重写       │
│   2. LimitListTushareFetcher (1.3) — 字段全部重写            │
│   3. HsgtTop10TushareFetcher (1.4) — 字段全部重写            │
│   4. ConceptSnapshotAdataFetcher (1.7) — 字段语义对齐         │
│   5. StockBasicTushareFetcher (1.1) — 补 4 字段              │
│   6. FinIncomeTushareFetcher (1.5) — 补 end_type              │
│   7. NewsTushareFetcher (1.6) — 字段重写 + 权限检测           │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ 第二批：P1 缺字段（建议 1 个 PR 一起做）                    │
│   8. SuspendTushareFetcher (2.1) — suspend_timing 不当 date │
│   9. MarginDetailTushareFetcher (2.3) — 补 name              │
│  10. DailyBasicTushareFetcher (2.7) — 补 limit_status        │
│  11. DividendTushareFetcher (2.8) — 补 2 字段                │
│  12. ConceptListAdataFetcher (2.9) — 补 source               │
│  13. ConceptMembersAdataFetcher (2.10) — 补 short_name       │
│  14. StockConceptsAdataFetcher (2.11) — 调字段 + 映射         │
│  15. HolderNumberTushareFetcher (2.6) — 补 holder_nums        │
│  16. BlockTradeTushareFetcher (2.2) — import 整理             │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ 第三批：P3 架构（fetcher → BO 解耦，独立 PR）                │
│  17. list[dict] → list[BaseModel] 改造（7 个 fetcher）        │
│  18. P2 入参扩展 / 限量循环 / 积分注释                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. 修复后预期

| 项 | 当前 | 修复后 |
|---|---|---|
| P0 严重不一致 | 8 处 | 0 |
| P1 缺字段 | 13 处 | 0 |
| fetcher 与表字段对齐 | 14/27 (52%) | 27/27 (100%) |
| fetcher 与文档接口字段对齐 | 14/27 (52%) | 27/27 (100%) |
| 返回类型规范（BO）| 20/27 (74%) | 27/27 (100%)（第三批完成后）|

---

## 7. 验收清单

第一、二批完成后，应当满足：

- [ ] 所有 27 个 fetcher 的 `_parse` 字段名与 `docs/backend-docs/data/{tushare,adata,pytdx}.md` 完全一致
- [ ] 所有 fetcher 写库的字段在对应表的列中存在
- [ ] 跑 `python -m scripts.verify_raw_db_deep` 仍然 30/30 OK
- [ ] 单元测试：每个 fetcher mock 一行 SDK 返回，断言 `BO` 字段全部就位
- [ ] 集成测试：每个 fetcher 调一次真接口（小额），数据能写入对应表

第三批完成后，应当满足：

- [ ] 所有 fetcher 返回 `list[BaseModel]`，不再有 `list[dict]`
- [ ] 所有 fetcher 入参模型（`*Params`）覆盖文档可传入参
- [ ] NewsTushareFetcher 增加权限检测，权限不足时**不写库**仅日志告警

---

## 8. 相关文档

- **数据接口文档**：`docs/backend-docs/data/{tushare,adata,pytdx}.md`
- **DDL 修复方案**（已完成）：[01-字段对账与修复方案.md](../01接口文档-数据库/01-字段对账与修复方案.md)
- **当前 30 张表清单**：[02-raw_data表清单.md](../02-raw_data表清单.md)
- **fetcher 基类**：`backend/src/contexts/collect/infrastructure/fetcher/base.py`
- **Tushare parser**：`backend/src/contexts/collect/infrastructure/parser/tushare.py`
- **Adata parser**：分散在 `ConceptListAdataFetcher.py` 的工具函数
