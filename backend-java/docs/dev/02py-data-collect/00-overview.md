# 00 整体架构、安全设计、服务调用链路

> 三个服务（前端 / Java / Python）的部署拓扑、数据流、安全机制、调用链路一览。

---

## 1. 部署拓扑

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            部署拓扑（推荐）                                   │
└─────────────────────────────────────────────────────────────────────────────┘

                ┌───────────────────────┐
                │  Browser (前端)        │
                │  Vue 3 + Vite + TS    │
                └──────────┬────────────┘
                           │ HTTPS + JWT
                           ▼
        ┌──────────────────────────────────────┐
        │  Nginx 反向代理（外网入口）            │
        │  - TLS 终结                          │
        │  - 静态资源（前端 dist）              │
        │  - /api/* → Java 8000                │
        │  - /ws/*  → Java 8000                │
        └──────────┬───────────────────────────┘
                   │ HTTP（内网）
                   ▼
        ┌──────────────────────────────────────┐
        │  backend-java (Spring Boot)          │
        │  - Port 8000                         │
        │  - 业务编排 + 入库 + 任务进度         │
        │  - 唯一对外出口                       │
        └─────┬────────────────────────┬───────┘
              │                        │
              │ JPA                    │ HTTP + HMAC（内网）
              ▼                        ▼
   ┌────────────────────┐    ┌──────────────────────────┐
   │  PostgreSQL 16     │    │  data-collector (Python)  │
   │  - 业务库          │    │  - Port 9100             │
   │  - 数据采集任务表   │    │  - FastAPI + uvicorn     │
   └────────────────────┘    │  - 无状态（多副本）       │
                            │  - 仅内网可达             │
   ┌────────────────────┐    └──────┬───────────────────┘
   │  Redis 7           │           │
   │  - 任务进度        │           │ HTTPS / HTTP（外网）
   │  - 短期缓存        │           ▼
   └────────────────────┘    ┌──────────────────────────────────┐
                             │  上游数据源                       │
                             │  - tushare.pro (HTTP REST)        │
                             │  - push2his.eastmoney.com (HTTP) │
                             │  - push2.eastmoney.com (HTTP)    │
                             │  - image.sinajs.cn (HTTP)        │
                             │  - pytdx (TCP, 备用)             │
                             └──────────────────────────────────┘
```

**关键约束**：
- **Python 服务无外网入口**：仅监听内网网卡（`0.0.0.0:9100` 改为 `10.0.0.0/8` 网卡），通过防火墙只允许 Java 主机访问。
- **Java 是唯一对外入口**：前端不直接调 Python。
- **采集入库位置（混合方案，按数据类型分流）**：

| 数据类型 | 采集 + 入库 | 说明 |
| --- | --- | --- |
| 日 K / 财报 / 资金 / 龙虎榜 / 股票基础 / 概念板块 | **Python 一条龙：拉 → 清洗 → 算指标 → 直连 DB upsert** | 大批量，避免 JSON 序列化/反序列化损耗，性能提升 5-10x |
| 分 K（即时查询） | **Python 仅查询不落库** → Java 透传 + Redis 缓存 | 小数据，不入库 |
| 业务写入（池操作、用户操作） | Java → DB | 业务逻辑在 Java，不下沉 |

> ⚠️ **Phase 1 实施范围**：本工程先实现 Python **采集 + 内存组装明细**，**不直接入库**；HTTP 返回明细 JSON 给 Java，Java 仍负责入库。
> Phase 2（后续 PR）再切到"Python 直连 DB"模式，届时需在 Java 端**配套引入受限数据库账号**（详见 `00-overview.md §1.1 待办`）。

### 1.1 待办（Phase 2）

- 创建 PostgreSQL 受限账号 `collector_writer`（仅 `INSERT/UPDATE`，无 `DDL/DELETE`）
- Python 端引入 SQLAlchemy + pandas_ta 指标库
- Java 端删除 `TechKlineDailyRepository.saveAll` / `IndicatorCalculator.enrich` 等采集相关 JPA 调用
- 接口响应契约从「明细 items」改为「摘要 fetched/saved/source」
- 详见 `05-migration-plan.md` Phase 2

---

## 2. 数据流分类

### 2.1 大数据量采集（批量入库）

> 当前实现：Python 采集 → 返回明细 JSON → Java 入库。
> **Phase 2 改造**：Python 采集 → Python 直连 DB 入库 → Java 仅收摘要。

```
用户/定时任务                Java 侧                       Python 侧                  上游
─────────────             ────────────                   ────────────              ──────
前端点击触发      →   POST /api/v1/collect/tasks
                          │  CollectController
                          ▼
                       CollectTaskService
                          │  异步执行（@Async）
                          ▼
                       KlineCollectTask.processOne(symbol)
                          │  HTTP /v1/collect/kline/daily  (HMAC)
                          ▼
                                              DataCollectorPort.fetchDailyKline()
                                                     │
                                                     ▼
                                              PythonKlineAdapter  ──────►  tushare.daily()
                                                     │ fallback                ▲
                                                     ▼                         │
                                              akshare.stock_zh_a_hist()  ─────┘
                                                     │
                                                     │ [当前] 返回明细 items
                                                     │ [Phase2] Python 直连 DB
                                                     │
                          ◄──────── JSON ───────────┘
                          │
                          ▼                  [当前] TechKlineDailyRepository.saveAll()
                       TechKlineDailyEntity     [当前] IndicatorCalculator.enrich()
                          │                     [当前] saveAll again
                          ▼
                       PostgreSQL ◄──── [当前] JPA 写入
                          │             [Phase2] Python 已写完
                          ▼
                       Redis: collect:progress:{taskId} 更新
                          │
                          ▼
                       SysCollectTaskDetailRepository.save()
```

### 2.2 小数据量查询（即时透传）

```
前端图表                Java 侧                          Python 侧
─────────────         ────────────                     ────────────
点击分K图表    →   GET /api/v1/kline/minute?symbol=000001&interval=5min&count=240
                     │  MinuteKlineController
                     ▼
                  Redis: 查 mk:{symbol}:{interval} 缓存
                     │ miss
                     ▼
                  HTTP /klines/minute (HMAC)
                                              PythonMinuteKlineAdapter
                                                     │
                                                     ▼
                                              push2his.eastmoney.com (首选)
                                                     │ fallback
                                                     ▼
                                              image.sinajs.cn
                     ◄────── JSON ─────────┘
                     │
                     ▼
                  Redis: setex mk:{symbol}:{interval} 30
                     │
                     ▼
                  Response → 前端
```

---

## 3. 服务间安全设计

> 三类调用链路的安全要求不同，分层设计。

### 3.1 前端 → Java（外网）

| 机制            | 实现                                                  |
| --------------- | ----------------------------------------------------- |
| 传输加密        | HTTPS（TLS 1.2+，Nginx 终结）                        |
| 身份认证        | JWT（HS256 / RS256，前端登录后获取 `access_token`）    |
| 权限校验        | Spring Security `@PreAuthorize`（按角色）             |
| 限流            | Nginx `limit_req` + Redis 滑动窗口                    |
| 防重放          | JWT `iat` + `exp`，Redis 黑名单                        |
| CORS            | Nginx 仅允许指定 origin                                |

> 既有方案，保持不变。

### 3.2 Java → Python（内网，必须强校验）

> **关键**：Python 虽在内网，但任何内网服务都不应"裸奔"。万一 Nginx 配置失误或内网机器失陷，必须有第二道防线。

| 机制             | 实现                                                                                          |
| ---------------- | --------------------------------------------------------------------------------------------- |
| 网络隔离         | Python 仅监听 `10.0.0.0/8` 网卡；防火墙只允许 Java 主机访问                                     |
| **HMAC 签名**    | 每个请求携带 `X-Signature` / `X-Timestamp` / `X-Nonce`，Java 用共享密钥 `INTERNAL_HMAC_SECRET` 计算 HMAC-SHA256，Python 验签 |
| 时间戳防重放     | `X-Timestamp` 与当前时间差 > 60s 直接拒绝                                                     |
| Nonce 防重放     | Java → Python 每次请求生成 UUID nonce，Python 用 Redis（带 TTL）记录 5 分钟内已用 nonce          |
| **IP 白名单**    | Python 启动时加载 `INTERNAL_ALLOWED_IPS`（Java 主机内网 IP），不匹配直接 403                    |
| **共享密钥轮转** | `INTERNAL_HMAC_SECRET` 通过 Vault / 环境变量注入，支持双密钥灰度轮转                            |
| **限流**         | Python 侧按 IP 限速（如 `slowapi`），防止内部被刷爆                                            |
| **审计日志**     | 所有 Java → Python 请求写 `audit.log`（含 method / path / signature / result / duration）     |

#### HMAC 签名算法

```
签名串（按字典序拼接）=
    METHOD + "\n" +
    PATH   + "\n" +     // 例 /collect/kline/daily
    QUERY  + "\n" +     // 例 symbol=000001&start_date=20250101
    BODY   + "\n" +     // JSON body（GET 时为空字符串）
    TIMESTAMP + "\n" +
    NONCE

签名 = HMAC-SHA256(签名串, INTERNAL_HMAC_SECRET)
       结果以 hex 编码
       放入请求头 X-Signature

请求头：
  X-Signature:  3f9c2a...
  X-Timestamp:  1735620000      // Unix 秒
  X-Nonce:      uuid4().hex
  X-Service:    backend-java
```

Java 端实现（伪代码）：
```java
String ts = String.valueOf(Instant.now().getEpochSecond());
String nonce = UUID.randomUUID().toString().replace("-", "");
String signString = method + "\n" + path + "\n" + query + "\n" + body + "\n" + ts + "\n" + nonce;
String signature = HmacUtils.hmacSha256Hex(secret, signString);
httpHeaders.set("X-Signature", signature);
httpHeaders.set("X-Timestamp", ts);
httpHeaders.set("X-Nonce", nonce);
```

Python 端验签（伪代码）：
```python
def verify_signature(req: Request):
    sig = req.headers.get("X-Signature")
    ts = req.headers.get("X-Timestamp")
    nonce = req.headers.get("X-Nonce")
    service = req.headers.get("X-Service")

    # 1. 来源服务必须是 backend-java
    if service != "backend-java":
        raise HTTPException(403, "invalid service")

    # 2. 时间戳防重放
    if abs(int(time.time()) - int(ts)) > 60:
        raise HTTPException(401, "timestamp expired")

    # 3. Nonce 一次性（Redis SETNX，TTL 300s）
    if not redis.set(f"nonce:{nonce}", "1", nx=True, ex=300):
        raise HTTPException(401, "nonce reused")

    # 4. 重算 HMAC
    body = await req.body()  # 只能读一次
    sign_str = f"{req.method}\n{req.url.path}\n{req.url.query}\n{body.decode()}\n{ts}\n{nonce}"
    expected = hmac.new(SECRET.encode(), sign_str.encode(), hashlib.sha256).hexdigest()

    # 5. 常量时间比较
    if not hmac.compare_digest(expected, sig):
        raise HTTPException(401, "bad signature")
```

### 3.3 Python → 上游数据源（公网）

| 数据源              | 安全机制                                       |
| ------------------- | ---------------------------------------------- |
| tushare.pro         | Token（环境变量 `TUSHARE_TOKEN`），HTTPS       |
| push2his.eastmoney  | 仅 HTTPS，无鉴权，靠 UA + Referer 防反爬       |
| push2.eastmoney     | 同上                                           |
| image.sinajs.cn     | HTTPS，Referer 必填                            |
| pytdx (TCP)         | 通达信协议公开服务器，无鉴权                    |

> Python 服务只出公网（防火墙出向放通），不暴露任何入站公网接口。

### 3.4 Secret 管理

| Secret               | 存储                          | 注入方式                       |
| -------------------- | ----------------------------- | ------------------------------ |
| `TUSHARE_TOKEN`      | Java/Python 环境变量          | K8s Secret / docker-compose env |
| `INTERNAL_HMAC_SECRET` | 仅 Python 启动环境            | K8s Secret，仅 Python 持有（Java 端硬编码在 `application.yml`，未来可改为 Vault） |
| `JWT_SECRET`         | Java 启动环境                  | 既有方案，保持不变             |

> **对称设计**：Java 计算签名需持有同一密钥。生产环境推荐 Java 与 Python 都从同一 Vault 路径读取，避免密钥不一致。

---

## 4. 调用链路（端到端）

### 4.1 手动触发日 K 采集

```
1. 用户在 collect-manage 页面点击「触发日K采集」
2. 前端 POST /api/v1/collect/tasks
   body: { taskType: "kline_daily", params: { symbols: ["000001.SZ"], days: 500 } }
3. Java CollectController.triggerTask()
4. Java CollectTaskService.triggerTask()
   └─> 创建 SysCollectTaskEntity（status=running）
   └─> @Async 提交到线程池
       └─> KlineCollectTask.executeAsync()
           └─> 对每个 symbol:
               KlineCollectTask.processOne(symbol)
                 └─> DataCollectorPort.fetchDailyKline(symbol, start, end)
                       └─> PythonKlineAdapter.fetchDailyKline()
                             └─> HTTP POST /v1/collect/kline/daily
                                  headers: X-Signature / X-Timestamp / X-Nonce / X-Service
                                  body:    { symbol, start_date, end_date, adj }
                             ◄─ JSON: { source, items: [...] }   [当前]
                             ◄─ JSON: { source, fetched, saved }  [Phase2]
                       └─> [当前] 解析为 List<TechKlineDailyEntity>
                       └─> [当前] TechKlineDailyRepository.saveAll()
                       └─> [当前] IndicatorCalculator.enrich(symbol)
                       └─> [当前] TechKlineDailyRepository.saveAll()
                 └─> 返回 saved count
                 └─> 更新 SysCollectTaskDetailEntity
                 └─> 更新 Redis: collect:progress:{taskId}
           └─> 全部完成后更新 SysCollectTaskEntity.status=success
5. 前端轮询 GET /api/v1/collect/tasks/{taskId}/progress
6. Java 读 Redis 返回进度 → 前端展示
```

### 4.2 前端查询分 K

```
1. 用户点击 K 线图 → 选择「5 分钟」
2. 前端 GET /api/v1/kline/minute?symbol=000001&interval=5min&count=240
3. Java MinuteKlineController.getMinuteKline()
4. Redis 查 mk:000001:5min（30s 缓存）
   └─ hit: 直接返回
   └─ miss:
       DataCollectorPort.fetchMinuteKline(symbol, interval, count)
         └─> PythonMinuteKlineAdapter
               └─> HTTP GET /klines/minute
                    headers: HMAC 签名
                    query:  symbol=000001&interval=5min&count=240
               ◄─ JSON: { source, items: [{datetime, open, close, ...}] }
         └─> 解析为 List<MinuteKlineVO>
         └─> Redis setex mk:000001:5min 30
5. Response → 前端图表渲染
```

### 4.3 定时任务自动采集

```
每日 17:00（交易日）
  ↓
Java @Scheduled cron="0 0 17 * * MON-FRI"
  ↓
CollectionScheduler.triggerDailyJobs()
  ├─> KlineCollectTask.executeAsync(params={days: 1})         // 当天日K
  ├─> DailyBasicCollectTask.executeAsync(params={days: 1})    // 当天估值
  ├─> MoneyflowCollectTask.executeAsync(params={days: 1})      // 当天资金流
  └─> ConceptSyncTask.executeAsync(source="akshare")
  ↓
每个任务走 4.1 链路
```

> **未来扩展**：股票基础信息每周一次（周一 09:00），财报每周一次，分红送股按公告事件触发。

---

## 5. 故障与降级

### 5.1 Python 服务不可用

| 现象                       | Java 端处理                                     |
| -------------------------- | ----------------------------------------------- |
| HTTP 超时                  | 重试 2 次（指数退避 1s/3s），仍失败则标记任务项失败 |
| 5xx                        | 重试 1 次，仍失败标记失败                       |
| 连接拒绝                   | 立即标记失败，不重试                             |
| HMAC 验签失败               | 记录告警（极可能是密钥不一致或被攻击），立即拒绝  |

### 5.2 数据源不可用

Python 端 fallback 链（详见 `01-python-architecture.md §4`）。

### 5.3 数据库不可用

- Java 端捕获 JPA 异常
- 任务标记失败，前端提示
- 采集进度 Redis 不受影响（已采集的明细不丢）

---

## 6. 监控与告警

| 指标                                 | 采集方   | 告警阈值        |
| ------------------------------------ | -------- | --------------- |
| Python 服务存活                       | Java 侧心跳 | 连续 3 次失败   |
| Python → tushare 成功率              | Python    | < 95%           |
| Java → Python 调用延迟 P99           | Java Micrometer | > 5s          |
| HMAC 验签失败次数                     | Python    | > 10/min        |
| Nonce 重放次数                        | Python    | > 0             |
| 任务执行耗时                          | Java      | > 30min         |
| 任务失败率                            | Java      | > 10%           |

---

## 7. 网络与端口规划

| 服务             | 端口  | 监听地址        | 入站 ACL                        |
| ---------------- | ----- | --------------- | ------------------------------- |
| frontend (dist)  | 80/443| 0.0.0.0         | 公网                            |
| backend-java     | 8000  | 0.0.0.0（仅 Nginx 反代可达） | 仅 Nginx 网段   |
| data-collector   | 9100  | 10.0.0.0/8 网卡 | 仅 Java 主机内网 IP             |
| PostgreSQL       | 5432  | 10.0.0.0/8      | 仅 Java                        |
| Redis            | 6379  | 10.0.0.0/8      | 仅 Java                        |
| tushare.pro      | 443   | -               | Python 出向放通                 |
| *.eastmoney.com  | 443   | -               | Python 出向放通                 |
| image.sinajs.cn  | 443   | -               | Python 出向放通                 |

---

## 8. 总结

| 调用方     | 被调方     | 安全机制                          |
| ---------- | ---------- | --------------------------------- |
| 前端       | Java       | HTTPS + JWT + Nginx 限流          |
| Java       | Python     | **内网 + HMAC 签名 + 时间戳 + Nonce + IP 白名单** |
| Python     | 上游数据源 | HTTPS + Token / Referer / UA      |

> 安全设计的核心思想：**纵深防御**——即使内网被攻破，没有共享密钥也调不动 Python；即使密钥泄露，没有内网 IP 也进不来。

---

## 9. 变更记录

| 版本  | 日期       | 变更人 | 变更内容 |
| ----- | ---------- | ------ | -------- |
| v0.1  | 2026-09-26 | -      | 初稿    |
