# 04 · 采集入库 + query service + 未实现接口清单

> 本文档三件事：
> 1. **采集入库**：哪些数据已持久化、哪些需要新建表
> 2. **Query service**：查询侧走 repo 还是调 fetcher + redis
> 3. **未实现接口**：哪些 fetcher 尚未写代码（planned / 尚未实现）

## 1. 核心判断逻辑

```
判断是否持久化 = 量大? OR AI分析需要?
├── 量大 + AI分析需要  → 持久化（已有表）
├── 量小 + AI分析需要  → 持久化（新建表）
├── 量小 + AI分析不需要 → 实时查询 + Redis缓存
└── 量大 + AI分析不需要 → ❌ 不做
```

## 2. 全部数据接口实现状态（5 个面 × 采集 + 查询）

> `✅ 已有` = ORM + task/fetcher 代码已实现；`⏳ 待建` = 表/ORM 未建；`❌ 未实现` = 代码未写；`⚠️ 占位` = PlannedCollectTask

### 2.1 技术面（tech）

| 数据 | 表 | 采集 task | 采集 ORM | 查询 service | 状态 |
|:--|:--|:--|:--|:--|:--|
| 日 K | `tech_kline_daily` | `DailyKlineCollectTask` | ✅ market ORM | `KlineDailyQueryService`（走 repo） | ✅ |
| 复权因子 | `tech_adj_factor` | 已有 | ✅ market ORM | — | ✅ |
| 交易日历 | `tech_calendar` | 已有 | ✅ market ORM | — | ✅ |
| 停复牌 | `tech_suspend` | 已有 | ✅ market ORM | — | ✅ |
| 股票曾用名 | `tech_name_change` | 已有 | ✅ market ORM | — | ✅ |
| **分 K（5/15/30/60 min）** | ❌ 无 | `MinuteKlineCollectTask`（占位） | ❌ | `KlineMinuteQueryService`（纯缓存） | ⚠️ 占位 |
| MA/EMA/MACD/RSI 等 | ❌ 无 | ❌ | ❌ | 应用层 pandas/talib 计算 | ❌ 不入库 |

### 2.2 资金面（capital）

| 数据 | 表 | 采集 task | 采集 ORM | 查询 service | 状态 |
|:--|:--|:--|:--|:--|:--|
| 个股资金流 | `capital_moneyflow` | 已有 | ✅ market ORM | `MoneyflowQueryService`（走 repo） | ✅ |
| 融资融券汇总 | `capital_margin` | 已有 | ✅ market ORM | `MarginQueryService`（走 repo） | ✅ |
| 融资融券明细 | `capital_margin_detail` | 已有 | ✅ market ORM | — | ✅ |
| 龙虎榜 | `capital_top_list` | 已有 | ✅ market ORM | `TopListQueryService`（走 repo） | ✅ |
| 龙虎榜机构席位 | `capital_top_inst` | 已有 | ✅ market ORM | — | ✅ |
| 大宗交易 | `capital_block_trade` | 已有 | ✅ market ORM | — | ✅ |
| 股东户数 | `capital_holder_num` | 已有 | ✅ market ORM | — | ✅ |
| **沪深港通资金流** | `capital_moneyflow_hsgt`（**新建**） | ❌ 待建 | ❌ 待建 | `MoneyflowHsgtQueryService`（先查库） | ⏳ |
| **沪深港通前 10 持仓** | `capital_hsgt_top10`（**新建**） | ❌ 待建 | ❌ 待建 | `HsgtTop10QueryService`（先查库） | ⏳ |
| **每日涨停板** | `market_limit_list`（**新建**） | ❌ 待建 | ❌ 待建 | `LimitListDQueryService`（先查库） | ⏳ |

### 2.3 基本面（fundamental）

| 数据 | 表 | 采集 task | 采集 ORM | 查询 service | 状态 |
|:--|:--|:--|:--|:--|:--|
| 股票基本信息 | `fundamental_stock_info` | `StockBasicCollectTask` | ✅ market ORM | `StockQueryService`（走 repo） | ✅ |
| 日频估值（PE/PB/PS） | `fundamental_daily_basic` | 已有 | ✅ market ORM | — | ✅ |
| 财务报表 | `fundamental_report` | 已有 | ✅ market ORM | — | ✅ |
| 前 10 大股东 | `fundamental_top10` | 已有 | ✅ market ORM | — | ✅ |
| 前 10 大流通股东 | `fundamental_top10_float` | 已有 | ✅ market ORM | — | ✅ |
| 分红送股 | `fundamental_dividend` | 已有 | ✅ market ORM | — | ✅ |
| 板块成分股 | `fundamental_index_member` | 已有 | ✅ market ORM | — | ✅ |
| 板块行情 | `fundamental_sector_daily` | 已有 | ✅ market ORM | — | ✅ |
| 大盘行情（指数） | `fundamental_market_daily` | 已有 | ✅ market ORM | `IndexQueryService`（走 repo） | ✅ |
| 概念列表 | `fundamental_concept` | `ConceptListCollectTask` | ✅ | `ConceptQueryService`（走 repo） | ✅ |
| 概念成分股 | `fundamental_concept_member` | `ConceptMembershipCollectTask` | ✅ | `ConceptQueryService`（走 repo） | ✅ |
| 概念行情快照 | `fundamental_concept_snapshot` | `ConceptSnapshotCollectTask` | ✅ | — | ✅ |
| 概念指数日 K | `fundamental_concept_index` | `ConceptIndexTHCollectTask` | ✅ | — | ✅ |

### 2.4 新闻面（news）

| 数据 | 表 | 采集 task | 采集 ORM | 查询 service | 状态 |
|:--|:--|:--|:--|:--|:--|
| **新闻快讯** | `news_article`（**新建**） | `NewsArticleCollectTask`（占位） | ❌ 待建 | `NewsQueryService`（先查库） | ⏳ |

### 2.5 情绪面（sentiment）

| 数据 | 表 | 采集 task | 采集 ORM | 查询 service | 状态 |
|:--|:--|:--|:--|:--|:--|
| 股吧/雪球帖子 | `sentiment_post` | ❌ | ❌ | ❌ | ❌ 待规划 |
| 每日情绪打分 | `sentiment_score_daily` | ❌ | ❌ | ❌ | ❌ 待规划 |
| 市场情绪指数 | `sentiment_index` | ❌ | ❌ | ❌ | ❌ 待规划 |

---

## 3. 未实现接口清单（需要新建）

### 3.1 需要新建 4 张表 + ORM

| # | 表名 | 数据来源 | Tushare 接口 | 量级 | AI 价值 | 建表优先级 |
|:--|:--|:--|:--|:--|:--|:--|
| 1 | `capital_moneyflow_hsgt` | 沪深港通资金流 | `moneyflow_hsgt` | 极小（每天 3-5 行） | ⭐⭐⭐ 高 | P0 |
| 2 | `capital_hsgt_top10` | 沪深港通前 10 持仓 | `hsgt_top10` | 小（每天几百行） | ⭐⭐⭐ 高 | P0 |
| 3 | `market_limit_list` | 每日涨停板 | `limit_list_d` | 小（每天几十-200 行） | ⭐⭐⭐ 高 | P0 |
| 4 | `news_article` | 新闻快讯 | `news`（需单独权限） | 中高（每天几百条） | ⭐⭐⭐⭐ 极高 | P1 |

**DDL 示例**：

```sql
-- 1. 沪深港通资金流（北向）
CREATE TABLE capital_moneyflow_hsgt (
    id          SERIAL PRIMARY KEY,
    trade_date  DATE NOT NULL,
    exchange    VARCHAR(8) NOT NULL,         -- SH/SZ/HK
    buy_amount  DOUBLE PRECISION,             -- 买入额（元）
    sell_amount DOUBLE PRECISION,            -- 卖出额（元）
    net_amount  DOUBLE PRECISION,            -- 净买入额
    data_source VARCHAR(16) NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(trade_date, exchange)
);

-- 2. 沪深港通前 10 持仓
CREATE TABLE capital_hsgt_top10 (
    id            SERIAL PRIMARY KEY,
    trade_date    DATE NOT NULL,
    symbol        VARCHAR(10) NOT NULL,
    holding_days  INT,                       -- 持股天数
    share_ratio   DOUBLE PRECISION,          -- 持股占总股本比
    hold_amount   DOUBLE PRECISION,          -- 持仓市值（元）
    net_amount    DOUBLE PRECISION,          -- 净买入额
    data_source   VARCHAR(16) NOT NULL,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(trade_date, symbol)
);

-- 3. 每日涨停板
CREATE TABLE market_limit_list (
    id              SERIAL PRIMARY KEY,
    trade_date      DATE NOT NULL,
    symbol          VARCHAR(10) NOT NULL,
    name            VARCHAR(50),
    close_price     DOUBLE PRECISION,
    change_rate     DOUBLE PRECISION,        -- 涨跌幅
    limit_type      VARCHAR(8),              -- up_limit / down_limit
    board_count     INT,                     -- 连板数
    first_limit_time TIME,                   -- 首次涨停时间
    board_strength  DOUBLE PRECISION,        -- 封板强度
    reason          TEXT,                    -- 涨停原因
    data_source     VARCHAR(16) NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(trade_date, symbol)
);

-- 4. 新闻快讯
CREATE TABLE news_article (
    id            SERIAL PRIMARY KEY,
    published_at  TIMESTAMPTZ NOT NULL,
    title         VARCHAR(512) NOT NULL,
    content       TEXT,
    source        VARCHAR(64),              -- 来源（新浪/东方财富/财联社）
    symbols       VARCHAR(10)[],             -- 关联股票代码数组
    sentiment     DOUBLE PRECISION,         -- AI情感分数（-1~1），后续NLP模型填充
    category      VARCHAR(32),              -- 利好/利空/中性/行业
    url           VARCHAR(1024),
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source, url)
);
```

### 3.2 需要实现的 4 个 fetcher

| # | Fetcher | 接口 | 限频 | 状态 |
|:--|:--|:--|:--|:--|
| 1 | `MoneyflowHsgtTushareFetcher` | `moneyflow_hsgt` | 200/60s | ❌ 未实现 |
| 2 | `HsgtTop10TushareFetcher` | `hsgt_top10` | 200/60s | ❌ 未实现 |
| 3 | `LimitListDTushareFetcher` | `limit_list_d` | 100/60s | ❌ 未实现 |
| 4 | `NewsAdataFetcher` | `news`（adata 备用） | 100/60s | ❌ 未实现（占位已有） |

### 3.3 需要实现的 4 个采集 task

| # | Task | 采集对象 | 触发时机 |
|:--|:--|:--|:--|
| 1 | `MoneyflowHsgtCollectTask` | 沪深港通资金流 | 交易日收盘后 |
| 2 | `HsgtTop10CollectTask` | 沪深港通前 10 持仓 | 交易日收盘后 |
| 3 | `LimitListDCollectTask` | 每日涨停板 | 盘中实时 + 收盘后 |
| 4 | `NewsCollectTask` | 新闻快讯 | 盘中轮询（每 5 分钟） |

### 3.4 分 K 查询（纯缓存，不持久化）

| Fetcher | ORM | Task | Query | 说明 |
|:--|:--|:--|:--|:--|
| `MinuteKlineTushareFetcher` | ❌ 无 | `MinuteKlineCollectTask`（占位，未实现入库） | `KlineMinuteQueryService`（纯缓存） | 量大（每年 8700 万行），不持久化全量；AI 分析可按需存近 N 日 |

---

## 4. Query service 分类（持久化 vs 纯缓存）

### 4.1 持久化查询（先查库，未命中调 fetcher）

> 以下 6 个有对应持久化表——HTTP 查询先走 repo；当日数据缺失时才调 fetcher 补齐。

| # | service | 持久化表 | ORM | 查询路径 |
|:--|:--|:--|:--|:--|
| 1 | `IndexQueryService` | `fundamental_market_daily` | ✅ market ORM | 走 repo |
| 2 | `StockQueryService` | `fundamental_stock_info` | ✅ market ORM | 走 repo |
| 3 | `ConceptQueryService` | `fundamental_concept` / `_member` | ✅ market ORM | 走 repo |
| 4 | `MoneyflowHsgtQueryService` | `capital_moneyflow_hsgt` | ⏳ 待建 | 先查库，miss 时调 fetcher |
| 5 | `HsgtTop10QueryService` | `capital_hsgt_top10` | ⏳ 待建 | 先查库，miss 时调 fetcher |
| 6 | `LimitListDQueryService` | `market_limit_list` | ⏳ 待建 | 先查库，miss 时调 fetcher |
| 7 | `NewsQueryService` | `news_article` | ⏳ 待建 | 先查库，miss 时调 fetcher |

### 4.2 纯缓存查询（只调 fetcher + Redis，不写库）

| # | service | fetcher | 缓存 TTL | 说明 |
|:--|:--|:--|:--|:--|
| 1 | `KlineMinuteQueryService` | `MinuteKlineTushareFetcher` | 15s / 4h | 量大，不持久化全量 |
| 2 | `KlineDailyQueryService` | `KlineTushareFetcher` | ❌ | 业务表已落库，直接走 repo |
| 3 | `MoneyflowQueryService` | — | — | 直接走 repo（`capital_moneyflow` 已持久化） |
| 4 | `MarginQueryService` | — | — | 直接走 repo（`capital_margin` 已持久化） |
| 5 | `TopListQueryService` | — | — | 直接走 repo（`capital_top_list` 已持久化） |

> **原则**：已有持久化表 → 走 repo；无表 → 纯缓存；新增表 → 先查库再补 fetcher。

---

## 5. 与 task 的关系

| 维度 | task | query service |
|:--|:--|:--|
| 入口 | schedule 触发 / HTTP `POST /collect/jobs/{id}/run` | HTTP `GET /xxx` |
| 调 fetcher | ✅ 调 | ✅ 调 |
| 写 collect_jobs | ✅ | ❌ |
| 进度上报 | ✅ progress 写 Redis | ❌ |
| 限流 | ✅ `RedisCache.rate_limit` 滑动窗口 | ❌（单请求 1 次调用） |
| 并发 | ✅ `asyncio.Semaphore`（THROTTLE_GROUPS） | ❌（单请求） |
| 缓存 | ❌（采集要拿新数据） | ✅ service 自己 redis |
| 状态 | `pending/running/success/...` | 一次性 HTTP 响应 |
| 业务 | **入库** | **查询** |

---

## 6. 完整接口汇总表

### 6.1 采集侧（`POST /collect/...`）

| 路径 | 方法 | service | 说明 |
|:--|:--|:--|:--|
| `/collect/catalog` | GET | `CatalogService` | 任务目录 |
| `/collect/jobs` | GET | `JobService.list` | 任务列表 |
| `/collect/jobs` | POST | `JobService.create` | 创建任务 |
| `/collect/jobs/{id}` | GET | `JobService.get` | 任务详情 |
| `/collect/jobs/{id}` | DELETE | `JobService.delete` | 删除任务 |
| `/collect/jobs/{id}/run` | POST | `JobService.run_job_template` | 触发执行 |
| `/collect/jobs/{id}/cancel` | POST | `JobService.cancel` | 取消任务 |
| `/collect/jobs/{id}/progress` | GET | `JobService.progress` | 任务进度 |
| `/collect/schedules/restore` | POST | `JobService.restore_schedules` | 恢复调度 |

### 6.2 实时查询侧（`GET /...`）

| 路径 | service | 查询方式 | 缓存 |
|:--|:--|:--|:--|
| `GET /klines/minute` | `KlineMinuteQueryService` | 纯缓存（调 fetcher） | 15s/4h |
| `GET /klines/daily` | `KlineDailyQueryService` | 走 repo | — |
| `GET /moneyflow/hsgt/realtime` | `MoneyflowHsgtQueryService` | 先 repo 再 fetcher | ⏳ |
| `GET /moneyflow/hsgt/top10` | `HsgtTop10QueryService` | 先 repo 再 fetcher | ⏳ |
| `GET /limit/board` | `LimitListDQueryService` | 先 repo 再 fetcher | ⏳ |
| `GET /news/realtime` | `NewsQueryService` | 先 repo 再 fetcher | ⏳ |
| `GET /index/basic` | `IndexQueryService` | 走 repo | — |
| `GET /stocks/{symbol}` | `StockQueryService` | 走 repo | — |
| `GET /concepts/{code}/stocks` | `ConceptQueryService` | 走 repo | — |
| `GET /capital/moneyflow/{symbol}` | `MoneyflowQueryService` | 走 repo | — |
| `GET /capital/margin/{symbol}` | `MarginQueryService` | 走 repo | — |
| `GET /capital/top_list` | `TopListQueryService` | 走 repo | — |

---

## 7. 实施优先级

| 优先级 | 数据 | 理由 |
|:--|:--|:--|
| **P0** | 沪深港通资金流 + 前 10 + 涨停板 | AI 量化分析核心因子；Tushare 接口已有权限 |
| **P1** | 新闻快讯 | AI 舆情分析核心；adata 可作为 Tushare news 权限未开的替代 |
| **P2** | 分 K 入库（近 N 日） | AI 日内策略；可选——数据量大 |
| **长期** | 情绪面（股吧/雪球） | 需要爬虫 + NLP 模型，基础设施待建设 |

---

## 8. `shared` 复用汇总（全部复用工程已有）

| 共享能力 | 位置 | 被谁用 |
|:--|:--|:--|
| Redis 客户端（不健康缓存） | `shared/infrastructure/cache/redis_client.py` | `RedisCache` 内部 |
| Redis 业务工具（KV / 限流 / 集合） | `shared/infrastructure/cache/redis_cache.py` | **所有 query service + task 限流** |
| `market_session`（TTL / 交易时段） | `market/domain/services/market_session.py` | **所有 cache TTL 计算** |
| `TushareClient` / `AdataClient` | `collect/infrastructure/sdk/` | fetcher 注入 |
