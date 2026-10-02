# route/ 接口层分析

> 关联：[`00-总览与建议清单.md`](00-总览与建议清单.md) · [`../config/DDD.md` §2.3](../../config/DDD.md)

---

## 1. 当前文件清单

```
backend/src/route/
├── api/
│   ├── _response.py        ← 统一响应格式（R.ok / R.err / R.created / ...）
│   ├── router.py          ← 聚合所有 v1 router
│   └── v1/                ← 10 个 API router（按资源 / 功能划分）
│       ├── concept.py
│       ├── kline.py
│       ├── minute_kline.py
│       ├── panel.py
│       ├── pool.py
│       ├── stock.py
│       ├── stock_analysis.py
│       ├── collect_task.py
│       └── [concept.py]    ← 重复（git status 重名）
│       └── [collect_task.py] ← 重复（git status 重名）
│       └── [minute_kline.py] ← 重复（git status 重名）
└── dto/                   ← 接口层 DTO（与传输协议绑定）
    ├── page.py            ← 通用分页响应容器
    ├── request/
    │   ├── kline.py      ← KlineBO（内部 BO）、KlineCollectRequest/KlineQueryRequest/KlineDeleteRequest
    │   ├── concept.py     ← ConceptListBO / ConceptMinuteBO / ...
    │   ├── fin_daily_basic.py
    │   ├── fin_report.py
    │   ├── stock.py
    │   ├── stock_info.py
    │   ├── collect.py
    │   └── pool_operation.py
    └── response/
        ├── kline.py
        ├── concept.py
        ├── panel.py
        ├── pool.py
        ├── collect.py
        └── stock_analysis.py
```

---

## 2. Router 职责矩阵

| Router | 前缀 | 路由数 | 调用的 AppService | DI 工厂位置 |
|---|---|---|---|---|
| `concept.py` | `/api/v1/concepts` | ~7 | `ConceptAppService` | **inline**（`get_concept_app_service()` 在 router 内定义） |
| `kline.py` | `/api/v1/klines` | ~5 | `KlineAppService` | `infrastructure/config/di.py::get_kline_app_service()` |
| `minute_kline.py` | `/api/v1/minute-klines` | ~2 | — | 无（直接调 RealtimeQueryFramework） |
| `panel.py` | `/api/v1/panels` | ~3 | `StockPanelAppService` | `infrastructure/config/di.py::get_panel_app_service()` |
| `pool.py` | `/api/v1/pools` | ~10 | `StockPoolAppService` | **inline**（`get_pool_app_service()` 在 router 内定义） |
| `stock.py` | `/api/v1/stocks` | ~4 | `StockAppService` | **inline** |
| `stock_analysis.py` | `/api/v1/stocks/{symbol}/analysis` | 1 | `StockAnalysisAppService` | **inline** |
| `collect_task.py` | `/api/v1/collect` | ~8 | `CollectAppService` | 直接构造 `CollectAppService()` |

---

## 3. 发现的问题

### 3.1 DI 工厂分散（高优先级）

`kline.py` 和 `panel.py` 从 `infrastructure/config/di.py` 导入：
```python
from infrastructure.config.di import get_kline_app_service
```

其余 5 个 router（concept/pool/stock/stock_analysis/collect_task）在文件内部定义 `def get_xxx_service(...)` 工厂。

**问题**：同一模式（`Depends(get_db) → new RepoImpl → new AppService`）重复 5 次；维护成本高。

**建议**：
1. 把 `get_concept_app_service`/`get_pool_app_service`/`get_stock_app_service`/`get_stock_analysis_app_service` 全部移到 `infrastructure/config/di.py`。
2. route 层统一 `from infrastructure.config.di import get_xxx_app_service`。
3. **但 `CollectAppService` 例外**——它是独立构造，不走 Depends，保持在 route 内。

**ROI**：高。代码量多（约 2-3h），但消除 5 处重复，维护收益大。

### 3.2 git status 重复文件（清理）

git status 显示以下文件在 `route/api/v1/` 下重复出现：
- `concept.py`（出现 2 次）
- `collect_task.py`（出现 2 次）
- `minute_kline.py`（出现 2 次）

**原因**：glob 搜索时返回了两条结果（如 `/v1/concept.py` 和 `/v1/concept.py`），但实际只存在一份——这可能是 glob 对 Windows 路径大小写不敏感导致的重复计数（Windows 是大小写不敏感文件系统）。

**建议**：执行 `Get-ChildItem route/api/v1/*.py | Sort-Object Name` 确认唯一文件数。若真的只有一份，git status 的重复是 Windows 路径处理问题，不是文件问题。

### 3.3 `_response.py`（统一响应封装）

```python
def ok(data: Any = None, message: str = "success") -> dict:
    return {"code": 200, "message": message, "data": data}
```

**现状**：所有 10 个 router 都 `return R.ok(response.model_dump())`。

**问题**：
1. `"code"` 字段是**内部约定**，非标准 HTTP 状态码（FastAPI 本身返回 200/201/400...）。前端需要理解这套内部约定。
2. 错误响应用 `JSONResponse`，成功响应返回 `dict`——类型不一致。

**建议**：
- 方案 A（推荐）：保持现状。这是内部约定，已在前端和所有 router 中一致使用，修改需要前端同步改。**不推荐现在动**。
- 方案 B：改用 FastAPI `ResponseModel` + 统一异常处理器，所有响应走标准 HTTP 状态码。

### 3.4 `route/dto/request/` 里有业务 BO（混合）

```
dto/request/kline.py: KlineBO    ← 这是采集 fetcher 的输出 BO
dto/request/concept.py: ConceptMinuteBO / ConceptListBO ...
```

**问题**：按 `DDD.md §2.3`，DTO 应在 route 层（接口协议），但 BO（如 `KlineBO`）是**数据源层的内部对象**（tushare 解析结果），不应该出现在 route/dto。

**分析**：
- `KlineBO` 被 `TushareFetcher` 返回，被 `tushare.py` 内部使用
- `route/dto/request/kline.py` 导入了 `KlineBO`：
  ```python
  from route.dto.request.kline import KlineCollectRequest, KlineBO
  ```
- `KlineBO` 在 `persistence/models/` 层不使用（KlineRepoImpl 用 `KlineEntity` 而非 `KlineBO`）

**结论**：`KlineBO` 应该：
- 留在 `infrastructure/adapter/fetcher/tushare.py` 内部作为内部 BO
- 不导出到 `route/dto/request/`

⚠️ **实际检查**：`tushare.py:29` 导入 `from route.dto.request.kline import KlineBO`——这是 `infrastructure → route` 的**反向依赖**，违反分层原则。

**建议**：把 `KlineBO` 移到 `infrastructure/adapter/fetcher/` 内部（如 `fetcher/kline_bo.py`），从 `route/dto/request/kline.py` 移除。

### 3.5 `route/dto/page.py`（通用分页容器）

```python
class Page[T]:
    @classmethod
    def from_list(items, total, page, page_size): ...
```

**评价**：✅ **标准泛型分页**。`PanelAppService` 等返回 `Page[ConceptItemVO]`。

---

## 4. 推荐改造清单

### 4.1 必须做

| 编号 | 动作 | 工作量 |
|---|---|---|
| R1 | 把 concept/pool/stock/stock_analysis 的 AppService 工厂集中到 `infrastructure/config/di.py` | 2-3 h |
| R2 | 检查 `route/api/v1/` 下是否真的有重复文件（Windows glob 误报 vs 实际重名） | 5 min |
| R3 | `infrastructure/adapter/fetcher/tushare.py` 导入 `route.dto.request.kline` → 把 `KlineBO` 移出 `route/dto/request/`，放到 `infrastructure/adapter/fetcher/kline_bo.py` | 1 h |
| R4 | 同理检查 `FinDailyBasicBO`、`FinReportBO`、`ConceptMinuteBO` 等是否也从 route 层导出BO | 30 min |

### 4.2 建议做

| 编号 | 动作 | 工作量 |
|---|---|---|
| R5 | 给每个 router 的 `def get_xxx_service` 加类型注解（如 `-> ConceptAppService`） | 20 min |
| R6 | `collect_task.py` 中 `CollectAppService()` 直接构造改为工厂函数（即使不放在 di.py 也要统一风格） | 10 min |
| R7 | 给 `_response.py` 头注释加说明：code 字段是内部约定，前端需同步适配 | 2 min |

### 4.3 暂缓

| 编号 | 动作 | 原因 |
|---|---|---|
| R8 | 把 `"code"` 内部约定改为标准 HTTP 状态码 | 需前端同步，大改动 |
| R9 | 所有响应改用 Pydantic ResponseModel | 收益小，破坏现有简洁风格 |

---

## 5. 一句话总结

**Route 层是最薄的层，职责正确**（入口、参数校验、响应序列化）。**最大问题是 DI 工厂分散在 5 个 router 内，应该集中到 di.py；次大问题是 BO（如 KlineBO）反向依赖 route 层，应该把 BO 移入 fetcher 内部**。**这两个问题都是历史遗留，不会影响功能但会增加维护成本**，建议在下一个功能开发周期前修复。