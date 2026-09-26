# 01 Python 服务架构设计

> `data-collector`（FastAPI）工程的内部架构、模块划分、采集器实现、fallback 策略、可观测性。

---

## 0. 当前实施范围（Phase 1）

> **本 PR 实施 Phase 1**：Python 仅实现**采集 + 内存组装明细 + HTTP 返回 JSON**，**不直连数据库**。
> Java 端继续负责入库。
>
> Phase 2（不在本 PR 范围）才引入 SQLAlchemy + pandas_ta，Python 直接入库。
> 本文档同时给出两个阶段的设计，便于评审。

| 维度 | Phase 1（本 PR） | Phase 2（后续 PR） |
| --- | --- | --- |
| Python 入库 | ❌ 不入库 | ✅ 直连 DB（受限账号） |
| Python 返回 | 明细 `items: [...]` | 摘要 `{fetched, saved, source}` |
| Java 入库 | ✅ JPA `saveAll` | ❌ 改为读 DB 验数 |
| 指标计算 | Java `IndicatorCalculator` | Python `pandas_ta` |
| Python 数据库账号 | ❌ 无 | `collector_writer`（仅 INSERT/UPDATE） |

---

## 1. 技术栈

| 组件         | 选型                          | 理由                                       |
| ------------ | ----------------------------- | ------------------------------------------ |
| Web 框架     | **FastAPI 0.115+**            | 异步、Pydantic 校验、自动 OpenAPI 文档     |
| ASGI 服务器  | **uvicorn** (1 worker 多进程可)| 简单稳定，Nginx 反代友好                   |
| 数据获取     | **httpx** (async)             | 支持 async / 连接池 / HTTP/2               |
| tushare      | **tushare**                   | 官方 SDK，封装 Pro API                      |
| akshare      | **akshare**                   | 仅在兜底场景使用                           |
| pytdx        | **pytdx**                     | TCP 二进制协议（备用）                      |
| 数据校验     | **Pydantic v2**               | FastAPI 原生                                |
| 配置         | **pydantic-settings**         | 从环境变量读取                              |
| 限流         | **slowapi**                   | 基于 Redis 的限流中间件                    |
| 日志         | **loguru**                    | 结构化日志                                 |
| 指标         | **prometheus-client**         | `/metrics` 暴露                            |
| 进程管理     | **supervisor** / **gunicorn** | 多 worker 时建议 gunicorn + uvicorn worker |
| 容器         | **Docker（python:3.12-slim）** | 镜像预估 **300-400MB**（含 tushare/akshare 间接拉的 pandas/numpy） |

> ⚠️ **pandas/numpy 不是我们主动引入的**，是 tushare / akshare 的**强制间接依赖**：
> - tushare API 返回 `pd.DataFrame`
> - akshare `requires pandas>=2.0.0`
>
> 我们**自己代码里不 import pandas**——只在 collector 内部把 DataFrame 转成 `list[dict]`，业务层、序列化、HTTP 响应全部走纯 Python 类型。
> 指标计算放在 Java 侧（`IndicatorCalculator`），**Python 不引 `pandas_ta`**，避免再叠体积。
>
> **镜像体积优化措施**（详见 §10.2 Dockerfile）：
> - 使用 `python:3.12-slim` 而非完整镜像（节省 800MB）
> - 多阶段构建（builder + runtime）
> - `pip install --no-cache-dir`
> - 清理 `apt-get` 缓存与 `/tmp` 临时文件
> - **不用 alpine**——akshare 在 musl 上兼容性差，且节省空间有限

---

## 11.5 依赖分层（避免 Python 体积失控）

```
┌──────────────────────────────────────────────────────────┐
│ app/ 业务代码（我们自己写的）                                │
│  - 只用 Python 标准库 + pydantic + httpx + loguru          │
│  - 业务类型：list[dict] / dataclass / Pydantic model      │
│  - 不 import pandas / numpy                                │
└──────────────────────────────────────────────────────────┘
            ↓ 数据进入
┌──────────────────────────────────────────────────────────┐
│ collectors/ 适配器（tushare/akshare/eastmoney/sina）       │
│  - 这一层允许使用 pandas（因为 tushare/akshare 的 API 就是 DataFrame）│
│  - 出口函数**强制**转成 list[dict]，不让 DataFrame 渗透到上层 │
└──────────────────────────────────────────────────────────┘
            ↓
        tushare/akshare 等第三方库（间接带 pandas）
```

**强制约定**：
- `app/services/*.py`、`app/routers/*.py`、`app/schemas/*.py` **禁止** `import pandas`
- `app/collectors/*.py` **允许** `import pandas`，但 `BaseCollector.fetch()` 返回类型必须是 `list[dict]` 或 `list[PydanticModel]`
- 提交前 grep 校验：业务层零 pandas 引用
- CI 检查脚本（`scripts/check_no_pandas.sh`）：
  ```bash
  ! grep -rn "import pandas\|from pandas" app/services app/routers app/schemas
  ```
| **DB 客户端（Phase 2，暂不引入）** | — | Phase 2 才加 SQLAlchemy，且只在 service 层用，**collector 层仍只用 list[dict]** |
| **指标库（Phase 2，暂不引入）** | — | 指标计算仍在 Java 侧（`IndicatorCalculator`）；**Python 不引 `pandas_ta`**，避免体积爆炸 |

> **纯 Python wheel 安装，零 C++ 编译依赖**——akshare / tushare / pytdx / fastapi / uvicorn / httpx / pydantic / SQLAlchemy / pandas_ta 均无 native 编译。

> **Phase 1 本 PR**：使用 Phase 1 列出的基础栈（FastAPI / httpx / tushare / akshare / pytdx / pydantic / slowapi / loguru / prometheus-client / cachetools）。
> **Phase 2**：额外加 SQLAlchemy / psycopg[binary]（**不引** pandas_ta；指标仍在 Java 侧，或 Phase 2 自实现纯 Python 指标）。

---

## 2. 项目结构

```
data-collector/
├── Dockerfile
├── docker-compose.yml          # 本地联调
├── pyproject.toml              # Poetry 依赖
├── README.md
├── .env.example
│
├── app/
│   ├── main.py                 # FastAPI 应用入口 + lifespan
│   ├── config.py               # Settings (pydantic-settings)
│   │
│   ├── core/                   # 横切关注点
│   │   ├── security.py         # HMAC 验签、IP 白名单、nonce 校验
│   │   ├── ratelimit.py        # slowapi 实例
│   │   ├── logging.py          # loguru 配置
│   │   ├── errors.py           # 统一异常体系 + 异常处理 handler
│   │   └── http_client.py      # httpx.AsyncClient 单例（带连接池）
│   │
│   ├── routers/                # 路由层（对外 HTTP）
│   │   ├── klines.py           # /klines/*   实时查询（日/分K）
│   │   ├── collect.py          # /collect/*  批量采集
│   │   ├── basic.py            # /basic/*    股票基础信息
│   │   ├── fundamentals.py     # /fundamentals/*  财务
│   │   ├── capital.py          # /capital/*  资金/龙虎榜
│   │   ├── concepts.py         # /concepts/* 概念板块
│   │   ├── market.py           # /market/*   大盘/行业
│   │   └── health.py           # /health     健康检查
│   │
│   ├── services/               # 业务编排（按场景）
│   │   ├── kline_service.py    # 日K / 分K 编排（含 fallback）
│   │   ├── stock_basic_service.py
│   │   ├── concept_service.py
│   │   ├── fundamental_service.py
│   │   └── ...
│   │
│   ├── collectors/             # 数据源适配器（每个源一个）
│   │   ├── base.py             # Collector 抽象基类
│   │   ├── tushare_collector.py
│   │   ├── akshare_collector.py
│   │   ├── eastmoney_collector.py     # push2his.eastmoney.com
│   │   ├── sina_collector.py          # image.sinajs.cn
│   │   └── pytdx_collector.py         # TCP（备用）
│   │
│   ├── schemas/                # Pydantic DTO（接口契约）
│   │   ├── kline.py            # KlineItem, KlineResponse, MinuteKlineResponse
│   │   ├── stock_basic.py
│   │   ├── concept.py
│   │   └── common.py           # Source enum、错误响应
│   │
│   └── infra/                  # 基础设施
│       ├── tushare_client.py   # TushareApiClient（pro.api 单例）
│       ├── pytdx_pool.py       # pytdx 连接池（懒初始化）
│       └── cache.py            # 进程内 LRU（短 TTL 去重）
│
└── tests/
    ├── unit/
    │   ├── test_collectors/
    │   └── test_security.py
    └── integration/
        └── test_routers.py
```

---

# 3. BaseCollector 返回值统一约定

- `BaseCollector.fetch()` 的返回类型 **必须是 `list[dict]` 或 `list[PydanticModel]`**，**不允许返回 `pd.DataFrame`**
- collector 内部允许使用 pandas 处理 DataFrame，但**出口前必须转换**
- 这条约定是**强制**的——避免 DataFrame 渗透到 service / router 层

```python
# 反例（不允许）
class BadCollector(BaseCollector):
    async def fetch(self, **kwargs) -> pd.DataFrame:   # ❌
        return self._tushare.daily(...)

# 正例（推荐）
class GoodCollector(BaseCollector):
    async def fetch(self, **kwargs) -> list[dict]:    # ✅
        df = await self._tushare.daily(...)
        return df.to_dict(orient="records")
```

# 3. 核心抽象

### 3.1 Collector 抽象基类

```python
# app/collectors/base.py
from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from app.schemas.kline import KlineItem

T = TypeVar("T")  # 每种数据类型不同（日K/分K/概念/财务...）

class BaseCollector(ABC, Generic[T]):
    """所有数据源采集器的统一抽象。"""

    # 数据源标识（在响应里告诉 Java 是从哪拿的）
    name: str = "base"

    @abstractmethod
    async def fetch(self, **kwargs) -> list[T]:
        """子类必须实现：返回清洗后的结构化数据。"""
        raise NotImplementedError

    async def healthcheck(self) -> bool:
        """默认实现：拉一次最小数据验证可达性。"""
        return True
```

### 3.2 带 fallback 的编排器（以日 K 为例）

```python
# app/services/kline_service.py
from app.collectors.tushare_collector import TushareDailyKlineCollector
from app.collectors.akshare_collector import AkshareDailyKlineCollector
from app.collectors.eastmoney_collector import EastMoneyKlineCollector
from app.schemas.kline import KlineItem, KlineResponse
from app.schemas.common import Source

class KlineService:
    """日 K 编排：tushare 优先 → akshare 兜底 → eastmoney 最后兜底。"""

    def __init__(
        self,
        tushare: TushareDailyKlineCollector,
        akshare: AkshareDailyKlineCollector,
        eastmoney: EastMoneyKlineCollector,
    ):
        self._tushare = tushare
        self._akshare = akshare
        self._eastmoney = eastmoney

    async def fetch_daily(
        self, symbol: str, start_date: str, end_date: str, adj: str = "qfq"
    ) -> KlineResponse:
        # 首选：tushare（数据最干净、含复权）
        try:
            items = await self._tushare.fetch(
                symbol=symbol, start_date=start_date, end_date=end_date, adj=adj
            )
            if items:
                return KlineResponse(symbol=symbol, source=Source.TUSHARE, items=items)
        except (QuotaExceeded, NetworkError) as e:
            logger.warning(f"tushare failed for {symbol}: {e}, fallback to akshare")

        # 兜底 1：akshare
        try:
            items = await self._akshare.fetch_daily(
                symbol=symbol, start_date=start_date, end_date=end_date, adj=adj
            )
            if items:
                return KlineResponse(symbol=symbol, source=Source.AKSHARE, items=items)
        except Exception as e:
            logger.warning(f"akshare failed for {symbol}: {e}, fallback to eastmoney")

        # 兜底 2：eastmoney
        items = await self._eastmoney.fetch_daily(
            symbol=symbol, begin=start_date, end=end_date
        )
        return KlineResponse(symbol=symbol, source=Source.EASTMONEY, items=items)
```

### 3.3 路由层（FastAPI）

```python
# app/routers/klines.py
from fastapi import APIRouter, Depends, Query
from app.services.kline_service import KlineService
from app.schemas.kline import KlineResponse, MinuteKlineResponse
from app.core.dependencies import get_kline_service

router = APIRouter(prefix="/klines", tags=["klines"])

# 即时查询（前端 → Java → 这里）
@router.get("/minute", response_model=MinuteKlineResponse)
async def get_minute_kline(
    symbol: str = Query(..., min_length=6, max_length=6),
    interval: str = Query("5min", regex="^(1min|5min|15min|30min|60min)$"),
    count: int = Query(240, ge=1, le=800),
    service: KlineService = Depends(get_kline_service),
):
    """实时分 K 透传（不落库）。"""
    return await service.fetch_minute(symbol=symbol, interval=interval, count=count)
```

```python
# app/routers/collect.py
from fastapi import APIRouter, Depends
from app.schemas.kline import KlineRequest, KlineResponse
from app.services.kline_service import KlineService
from app.core.dependencies import get_kline_service

router = APIRouter(prefix="/collect", tags=["collect"])

# 批量采集（Java 内部调用）
@router.post("/kline/daily", response_model=KlineResponse)
async def collect_daily_kline(
    body: KlineRequest,
    service: KlineService = Depends(get_kline_service),
):
    """批量日 K 采集（Java 写入 DB 后再调一次）。"""
    return await service.fetch_daily(
        symbol=body.symbol,
        start_date=body.start_date,
        end_date=body.end_date,
        adj=body.adj,
    )
```

---

## 4. 数据源 Fallback 矩阵

| 场景             | 首选                | 兜底 1              | 兜底 2             | 备注                                       |
| ---------------- | ------------------- | ------------------- | ------------------ | ------------------------------------------ |
| 日 K（A股）      | tushare.daily       | akshare.stock_zh_a_hist | eastmoney.push2his | tushare 需 2000+ 积分；积分不够自动降级     |
| 分 K（5/15/30/60min） | eastmoney.push2his | sina.image.sinajs.cn | -                  | tushare 仅 1/5/15/30/60min，但有配额      |
| 分 K（1min）     | eastmoney.push2his  | sina（仅当日）      | -                  | 仅当日 240 根左右                           |
| 股票基础信息     | tushare.stock_basic | akshare.stock_info_a_code_name | eastmoney | tushare 最全                               |
| 财务三大表       | tushare（income/balancesheet/cashflow）| akshare（部分）| -        | 财报仅 tushare 全                          |
| 日频估值（PE/PB等）| tushare.daily_basic | akshare（部分）      | -                  | -                                          |
| 资金流向         | tushare.moneyflow   | akshare（资金流）    | eastmoney          | tushare 数据最准                            |
| 龙虎榜           | tushare.top_list    | akshare（龙虎榜）   | eastmoney          | -                                          |
| 大宗交易         | tushare.block_trade | eastmoney            | -                  | -                                          |
| 概念板块列表     | eastmoney.push2     | tushare.concept     | akshare            | eastmoney 概念最全                          |
| 概念成分股       | eastmoney.push2     | akshare             | -                  | -                                          |
| 交易日历         | tushare.trade_cal   | eastmoney（不公开） | -                  | -                                          |
| 大盘行情         | tushare.index_daily | eastmoney.push2his  | sina               | -                                          |
| 行业板块行情     | tushare.index_daily | akshare（行业板块） | eastmoney          | -                                          |
| 复权因子         | tushare.adj_factor  | -                   | -                  | 仅 tushare 有                               |
| 股东人数         | tushare.holder_num  | -                   | -                  | -                                          |
| 前十大股东       | tushare.top10_holders | -                | -                  | -                                          |
| 融资融券         | tushare.margin_detail | eastmoney          | -                  | -                                          |
| 分红送股         | tushare.dividend    | akshare             | eastmoney          | -                                          |

> **设计原则**：能不降级就不降级；降级时日志告警 + 指标计数；同一指标 fallback 链不超过 3 级。

---

## 5. 异常体系

```python
# app/core/errors.py
class CollectorError(Exception):
    """采集器通用错误。"""

class SourceUnavailable(CollectorError):
    """数据源不可用（网络/限流/服务端 5xx）。"""

class QuotaExceeded(CollectorError):
    """配额超限（tushare 积分 / IP 限流）。"""

class InvalidSymbol(CollectorError):
    """股票代码非法。"""

class DataQualityError(CollectorError):
    """返回数据解析失败或字段缺失。"""
```

FastAPI 全局异常处理：

```python
@app.exception_handler(SourceUnavailable)
async def source_unavailable_handler(request: Request, exc: SourceUnavailable):
    return JSONResponse(
        status_code=503,
        content={"code": 50301, "msg": f"upstream source unavailable: {exc}"},
    )
```

---

## 6. 可观测性

### 6.1 日志格式（JSON）

```json
{
  "ts": "2026-09-26T17:00:00.123+08:00",
  "level": "INFO",
  "service": "data-collector",
  "trace_id": "uuid",
  "method": "POST",
  "path": "/collect/kline/daily",
  "status": 200,
  "duration_ms": 245,
  "symbol": "000001.SZ",
  "source": "tushare",
  "items": 243,
  "msg": "fetch daily kline success"
}
```

### 6.2 Prometheus 指标

```
# HELP py_collect_requests_total Total data collection requests
# TYPE py_collect_requests_total counter
py_collect_requests_total{source="tushare", endpoint="kline_daily", status="success"} 12345

# HELP py_collect_request_duration_seconds Request duration
# TYPE py_collect_request_duration_seconds histogram
py_collect_request_duration_seconds_bucket{source="tushare", endpoint="kline_daily",le="0.5"} 11000

# HELP py_collect_fallback_total Total fallback events
# TYPE py_collect_fallback_total counter
py_collect_fallback_total{from_source="tushare", to_source="akshare", reason="quota"} 23

# HELP py_collect_signature_failures_total HMAC signature failures
# TYPE py_collect_signature_failures_total counter
py_collect_signature_failures_total{reason="expired"} 0
```

---

## 7. 进程模型与并发

### 7.1 单进程模型（默认）

```bash
uvicorn app.main:app --host 10.0.0.5 --port 9100 --workers 1 --log-level info
```

- **单 worker** 即可，因：
  - FastAPI 是 async（asyncio）
  - tushare / akshare 都是阻塞 IO → 放 `run_in_executor`
  - httpx 用连接池复用

### 7.2 多 worker（水平扩展）

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 10.0.0.5:9100
```

- 适合 QPS 上千的场景
- Tushare token 共享，无需 session 亲和

### 7.3 K8s 部署

- Deployment replicas=2~4，HPA 按 CPU 60%
- 无状态，无需 PVC
- 优雅停机：uvicorn `timeout_graceful_shutdown=30`

---

## 8. 缓存策略（进程内）

```python
# app/infra/cache.py
from cachetools import TTLCache

# 分钟 K 短期缓存（防 Java 端短时间内重复拉）
_minute_kline_cache: TTLCache = TTLCache(maxsize=2000, ttl=30)

# 股票基础信息（每日变化不大，缓存 5 分钟）
_basic_cache: TTLCache = TTLCache(maxsize=6000, ttl=300)

# 交易日历（缓存到当天 23:59）
_calendar_cache: TTLCache = TTLCache(maxsize=1, ttl=...)
```

> 注意：**进程内缓存不替代 Redis**。Java 侧 Redis 才是权威缓存。Python 进程内缓存仅用于"同一进程内短时间重复请求"的优化。

---

## 9. 配置（pydantic-settings）

```python
# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 服务
    host: str = "10.0.0.5"
    port: int = 9100
    workers: int = 1

    # 安全
    internal_hmac_secret: str           # 从环境变量 INTERNAL_HMAC_SECRET
    internal_allowed_ips: list[str]     # ["10.0.0.10", "10.0.0.11"]
    timestamp_tolerance_seconds: int = 60
    nonce_ttl_seconds: int = 300

    # 数据源
    tushare_token: str = ""             # TUSHARE_TOKEN
    eastmoney_base_url: str = "https://push2his.eastmoney.com"
    sina_base_url: str = "https://image.sinajs.cn"

    # 限流
    rate_limit_per_minute: int = 600

    # 日志
    log_level: str = "INFO"
    log_json: bool = True

    # 上游超时
    upstream_timeout_seconds: int = 8
    upstream_max_retries: int = 2

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## 10. 部署清单

### 10.1 Dockerfile（多阶段，镜像 < 200MB）

```dockerfile
FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry export -f requirements.txt --without dev -o req.txt && \
    pip wheel --wheel-dir=/wheels -r req.txt

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-index --find-links=/wheels fastapi uvicorn httpx tushare akshare pytdx pydantic pydantic-settings slowapi loguru prometheus-client cachetools && \
    rm -rf /wheels
COPY app ./app
ENV PYTHONUNBUFFERED=1
EXPOSE 9100
HEALTHCHECK --interval=30s --timeout=3s CMD curl -fsS http://localhost:9100/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9100"]
```

### 10.2 docker-compose.yml（本地联调）

```yaml
version: "3.8"
services:
  data-collector:
    build: .
    container_name: data-collector
    ports:
      - "9100:9100"
    environment:
      INTERNAL_HMAC_SECRET: "dev-secret-please-rotate"
      INTERNAL_ALLOWED_IPS: '["127.0.0.1","10.0.0.10"]'
      TUSHARE_TOKEN: "${TUSHARE_TOKEN}"
      LOG_LEVEL: "DEBUG"
    restart: unless-stopped
```

---

## 11. 总结

- **架构扁平**：路由 → service → collector → 数据源，每层只做一件事
- **fallback 矩阵明确**：每个数据点都有兜底链
- **可观测性内建**：JSON 日志 + Prometheus 指标 + 健康检查
- **无状态**：所有持久化在 Java 侧，Python 可以任意重启/扩缩
- **纯 Python 部署**：无 C++ 编译，镜像小，构建快

---

## 12. 变更记录

| 版本  | 日期       | 变更人 | 变更内容 |
| ----- | ---------- | ------ | -------- |
| v0.1  | 2026-09-26 | -      | 初稿    |
