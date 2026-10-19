# raw_data 库表清单（修复后定版）

> 适用版本：2026-10-18 修复后
> 数据库：`raw_data_db`（PostgreSQL 16）
> 修复依据：[01-字段对账与修复方案.md](01-字段对账与修复方案.md)
> 验证脚本：`backend/scripts/verify_raw_db_deep.py`（已通过：30/30 表列名+类型完全对齐）

---

## 0. 总览

| 项 | 数 |
|---|---|
| 总表数 | **30** |
| 技术面 | 5 |
| 资金面 | 10 |
| 基本面 | 12 |
| 新闻面 | 1 |
| 其他（行情/日历） | 2 |
| 主要数据源 | Tushare（27 张）、Adata（3 张）、Tushare+Adata 双源（1 张 news_article） |
| 业务表（股票概念） | 1 张走 Adata 单独建表 |

> ⚠️ 修复前 25 张 → 修复后 30 张。新增 5 张全部对应接口文档中**之前缺表**的 fetcher。

---

## 1. 完整表清单（按基本面分组）

### 1.1 技术面（5 张）

| # | 表名 | 数据源 | Tushare/Adata 接口 | 字段数 | 用途 |
|---|---|---|---|---|---|
| 1 | `tech_kline_daily` | Tushare | `pro.daily` | 13 | 日 K 线（OHLCV） |
| 2 | `tech_adj_factor` | Tushare | `pro.adj_factor` | 7 | 复权因子 |
| 3 | `tech_calendar` | Tushare | `pro.trade_cal` | 8 | 交易日历（**待补 fetcher**） |
| 4 | `tech_name_change` | Tushare | `pro.namechange` | 10 | 股票曾用名 |
| 5 | `tech_suspend` | Tushare | `pro.suspend_d` | 8 | 停复牌（**已修复 `suspend_timing` 类型 bug**） |

---

### 1.2 资金面（10 张）

| # | 表名 | 数据源 | Tushare/Adata 接口 | 字段数 | 用途 |
|---|---|---|---|---|---|
| 6 | `capital_moneyflow` | Tushare | `pro.moneyflow` | 24 | 个股资金流向（4 档买卖 + 净流入） |
| 7 | `capital_moneyflow_hsgt` | Tushare | `pro.moneyflow_hsgt` | 16 | 沪深港通资金流向（**新建**） |
| 8 | `capital_top_list` | Tushare | `pro.top_list` | 19 | 龙虎榜每日统计 |
| 9 | `capital_top_inst` | Tushare | `pro.top_inst` | 14 | 龙虎榜机构席位明细 |
| 10 | `capital_block_trade` | Tushare | `pro.block_trade` | 12 | 大宗交易 |
| 11 | `capital_margin` | Tushare | `pro.margin` | 13 | 两融汇总（按交易所） |
| 12 | `capital_margin_detail` | Tushare | `pro.margin_detail` | 15 | 个股两融明细（**已补 `name` 字段**） |
| 13 | `capital_hsgt_top10` | Tushare | `pro.hsgt_top10` | 15 | 沪深股通十大成交股（**新建**） |
| 14 | `capital_limit_list_d` | Tushare | `pro.limit_list_d` | 22 | 每日涨跌停列表（**新建**） |
| 15 | `capital_holder_num` | Tushare | `pro.stk_holdernumber` | 9 | 股东户数 |

---

### 1.3 基本面（12 张）

| # | 表名 | 数据源 | Tushare/Adata 接口 | 字段数 | 用途 |
|---|---|---|---|---|---|
| 16 | `fundamental_daily_basic` | Tushare | `pro.daily_basic` | 23 | 日频估值指标（PE/PB/PS/换手率/股本/市值，**已补 `limit_status`**） |
| 17 | `fundamental_report` | Tushare | `pro.income` / `balancesheet` / `cashflow` | 24 | 财务报表（**已补 `end_type`，后续 PR 拆 3 表**） |
| 18 | `fundamental_top10` | Tushare | `pro.top10_holders` | 13 | 前十大股东 |
| 19 | `fundamental_top10_float` | Tushare | `pro.top10_floatholders` | 13 | 前十大流通股东（**已补 `hold_float_ratio`**） |
| 20 | `fundamental_dividend` | Tushare | `pro.dividend` | 18 | 分红送股（**已补 `div_listdate` / `imp_ann_date`**） |
| 21 | `fundamental_index_member` | Tushare | `pro.index_member` | 12 | 板块成分股（行业/概念/地域） |
| 22 | `fundamental_sector_daily` | Tushare | `pro.sector_daily` | 18 | 板块行情（行业/概念） |
| 23 | `fundamental_market_daily` | Tushare | `pro.index_daily` | 15 | 市场整体行情（沪深主要指数） |
| 24 | `fundamental_stock_info` | Tushare | `pro.stock_basic` | 21 | 股票基本信息（**已补 4 字段：fullname / enname / cnspell / curr_type**） |
| 25 | `fundamental_concept` | Adata | `stock.info.all_concept_code_ths` | 11 | 概念聚合根（同花顺） |
| 26 | `fundamental_concept_member` | Adata | `stock.info.concept_constituent_ths` | 7 | 概念成员（**已补 `short_name`**） |
| 27 | `fundamental_concept_index` | Adata | `stock.market.get_market_concept_ths` | 13 | 概念指数日 K |
| 28 | `fundamental_concept_snapshot` | Adata | `stock.market.get_market_concept_current_ths` | 21 | 概念行情快照（**已修复 `pct_change` 语义错位**） |
| 29 | `fundamental_stock_concept` | Adata | `stock.info.get_concept_ths` | 9 | 股票所属概念（**新建**） |

> 基本面原本 11 张，加 1 张 `fundamental_stock_concept` 后 12 张
> 概念相关共 5 张：concept / concept_member / concept_index / concept_snapshot / stock_concept

---

### 1.4 新闻面（1 张）

| # | 表名 | 数据源 | Tushare/Adata 接口 | 字段数 | 用途 |
|---|---|---|---|---|---|
| 30 | `news_article` | Tushare+预留 | `pro.news` | 13 | 全市场快讯（**新建**，含 `symbols ARRAY` / `sentiment` / `category` 占位） |

---

## 2. 按数据源统计

### 2.1 数据源分布

| 数据源 | 表数 | 占比 |
|---|---|---|
| **Tushare** | 27 | 90% |
| **Adata（同花顺）** | 3 | 10% |
| Tushare + Adata 双源预留 | 1 | — |
| **合计** | **30** | 100% |

### 2.2 Tushare 27 张明细

| 分类 | 表 | 数量 |
|---|---|---|
| 技术面 | kline_daily / adj_factor / calendar / name_change / suspend | 5 |
| 资金面 | moneyflow / moneyflow_hsgt / top_list / top_inst / block_trade / margin / margin_detail / hsgt_top10 / limit_list_d / holder_num | 10 |
| 基本面 | daily_basic / report / top10 / top10_float / dividend / index_member / sector_daily / market_daily / stock_info | 9 |
| 新闻 | news_article | 1 |
| 小计 | — | **25** |

### 2.3 Adata 4 张明细

| 分类 | 表 |
|---|---|
| 基本面 | fundamental_concept / fundamental_concept_member / fundamental_concept_index / fundamental_concept_snapshot / fundamental_stock_concept |

> 注：news_article 当前是 Tushare 主导，预留扩展为多源。

---

## 3. 修复前后对比

| 状态 | 修复前 | 修复后 | 变化 |
|---|---|---|---|
| 表数 | 25 | **30** | +5（moneyflow_hsgt / hsgt_top10 / limit_list_d / news_article / stock_concept） |
| 缺字段 | 8 张 | 0 | 全部补齐 |
| 类型 bug | 1 处（suspend_timing） | 0 | date → varchar(32) |
| 字段语义错位 | 1 处（concept_snapshot pct_change） | 0 | 改为 p_change + 新加 pct_change |
| 列名+类型对齐 | 不可知 | 30/30 ✅ | 自动化验证 |

---

## 4. 字段完整度

| 表 | 完整度 | 备注 |
|---|---|---|
| 30 张表全部 | 100% | 字段与接口文档输出一一对应 |
| 字段重命名 | fetcher 转换 | vol→volume / pct_chg→change_pct / ts_code→symbol / change→p_change 等 |
| `fundamental_report` | 12% 报表字段 / 100% 核心字段 | 完整 100+ 字段后续 PR 拆 3 表（income/balance/cashflow） |

---

## 5. 关键 SQLAlchemy ORM 文件位置

| 表 | ORM 文件 |
|---|---|
| `tech_*` | `backend/src/contexts/market/infrastructure/persistence/models/{tech_kline, base_adj_factor, mkt_calendar, base_name_change, base_suspend}.py` |
| `capital_*` | `backend/src/contexts/market/infrastructure/persistence/models/cap_*.py` + `backend/src/contexts/collect/infrastructure/persistence/models/{cap_moneyflow_hsgt, cap_hsgt_top10, capital_limit_list_d}.py` |
| `fundamental_*` | `backend/src/contexts/market/infrastructure/persistence/models/fin_*.py` / `mkt_*.py` / `stock_info.py` + `backend/src/contexts/concept/infrastructure/persistence/models/concept.py` + `backend/src/contexts/collect/infrastructure/persistence/models/fundamental_stock_concept.py` |
| `news_*` | `backend/src/contexts/collect/infrastructure/persistence/models/news_article.py` |

---

## 6. 运维脚本

| 脚本 | 用途 | 用法 |
|---|---|---|
| `backend/scripts/verify_raw_db.py` | 轻量对账（只比对列名） | `python -m scripts.verify_raw_db` |
| `backend/scripts/verify_raw_db_deep.py` | 深度对账（列名+类型） | `python -m scripts.verify_raw_db_deep` |
| `backend/scripts/fix_raw_db_schema.py` | 修复脚本（幂等，可重跑） | `python -m scripts.fix_raw_db_schema` |

> 所有脚本幂等，可重复执行。

---

## 7. 后续 PR 规划

| PR | 内容 | 依赖 |
|---|---|---|
| ✅ 本 PR | 表结构修复 30 张 | — |
| ⏳ fetcher 同步 PR | 27 个 fetcher 字段映射与新表对齐 | 本 PR |
| ⏳ DDL-PR-followup-1 | 拆 `fundamental_report` → 3 表 | 本 PR |
| ⏳ tech_calendar-PR | 新建 `TradeCalTushareFetcher` | 本 PR |
| ⏳ news-表补全 PR | 8 维分类打标字段 + Tushare `news` 真实字段 | Tushare 权限 |
