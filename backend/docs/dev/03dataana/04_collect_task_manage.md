# 采集任务管理 — 开发文档

> 数据类设计参见：`PlantUML/总体类设计/采集任务日志-数据类设计.md`
> UML 类图参见：`PlantUML/总体类设计/02_collect_task_log.puml`

## 一、概述

新增「数据采集」页面，统一管理所有数据源的采集操作，替代当前分散在股票列表页的同步按钮。

### 1.1 解决的问题

| 现状 | 目标 |
|:---|:---|
| 采集日K/估值/基本信息的按钮分散在股票列表工具栏 | 独立「数据采集」页面统一管理 |
| 采集进度用全局变量存储，服务器重启丢失 | PostgreSQL 持久化 + Redis 实时进度 |
| 无历史记录，不知道上次何时采集、结果如何 | 任务列表展示完整采集历史 |
| 无法区分增量/全量，参数固定 | 用户可选择日期范围和回溯天数 |

### 1.2 涉及模块

```
后端                                     前端
├─ ORM: sys_collect_task.py              ├─ views/data-collect/
│       sys_collect_task_detail.py       │   ├─ DataCollect.vue (主页面)
├─ Repository: collect_task_repo.py      │   └─ components/
├─ Service: collect_task_service.py      │       ├─ CollectPanel.vue (操作面板)
├─ Route: /api/v1/collect/               │       ├─ TaskProgress.vue (进度展示)
│   ├─ POST /tasks                       │       └─ TaskHistory.vue (历史记录)
│   ├─ GET  /tasks                       ├─ api: data-collect/api.ts
│   ├─ GET  /tasks/{id}                  └─ router: home.ts (新增菜单)
│   ├─ GET  /tasks/{id}/progress
│   └─ POST /tasks/{id}/cancel
├─ Alembic Migration
└─ Redis 进度缓存
```

## 二、后端实现

### 2.1 ORM 模型

**文件：** `backend/src/infrastructure/database/models/sys_collect_task.py`

```python
class SysCollectTaskDB(Base, TimestampMixin):
    __tablename__ = "sys_collect_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    trigger_type: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)
    skip_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
```

**文件：** `backend/src/infrastructure/database/models/sys_collect_task_detail.py`

```python
class SysCollectTaskDetailDB(Base):
    __tablename__ = "sys_collect_task_details"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("sys_collect_tasks.id"), index=True)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    saved_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
```

### 2.2 Alembic 迁移

```bash
cd backend
alembic revision --autogenerate -m "add sys_collect_tasks and details"
alembic upgrade head
```

### 2.3 API 路由设计

**文件：** `backend/src/route/api/v1/collect_task.py`

| 方法 | 路径 | 说明 |
|:---|:---|:---|
| POST | `/collect/tasks` | 创建并启动采集任务 |
| GET | `/collect/tasks` | 查询任务列表（分页，按时间倒序） |
| GET | `/collect/tasks/{id}` | 查询单个任务详情（含明细统计） |
| GET | `/collect/tasks/{id}/progress` | 实时进度（读 Redis） |
| POST | `/collect/tasks/{id}/cancel` | 取消运行中的任务 |

#### POST /collect/tasks — 创建任务

**请求体：**

```json
{
  "task_type": "daily_kline",
  "params": {
    "days": 7
  }
}
```

**处理流程：**

```
1. 检查是否有同 task_type 的 running 任务，有则拒绝
2. 创建 sys_collect_tasks 记录 (status='running')
3. 写 Redis collect:progress:{id} 初始值
4. 启动 BackgroundTask 执行采集
5. 立即返回 task_id + 总数
```

**响应：**

```json
{
  "code": 0,
  "data": {
    "task_id": 42,
    "task_type": "daily_kline",
    "total_count": 5326,
    "message": "已启动日K采集任务，共 5326 只股票，回溯 7 天"
  }
}
```

#### GET /collect/tasks — 任务列表

**查询参数：**

| 参数 | 类型 | 说明 |
|:---|:---|:---|
| task_type | str, optional | 按类型筛选 |
| status | str, optional | 按状态筛选 |
| page | int, default 1 | 页码 |
| page_size | int, default 20 | 每页条数 |

#### GET /collect/tasks/{id}/progress — 实时进度

从 Redis 读取，响应：

```json
{
  "code": 0,
  "data": {
    "total": 5326,
    "done": 1200,
    "success": 1195,
    "fail": 5,
    "skip": 0,
    "status": "running",
    "current": "002415",
    "percent": 22.5,
    "elapsed_ms": 45000
  }
}
```

### 2.4 后台任务执行逻辑

**采集入口统一为一个调度函数：**

```python
async def _execute_collect_task(task_id: int, task_type: str, params: dict):
    """统一的后台采集执行器"""

    handlers = {
        "daily_kline": _collect_daily_kline,
        "daily_basic": _collect_daily_basic,
        "stock_basic": _collect_stock_basic,
        "fin_report":  _collect_fin_report,
    }

    handler = handlers.get(task_type)
    if not handler:
        raise ValueError(f"未知的任务类型: {task_type}")

    await handler(task_id, params)
```

**单个 handler 示例（daily_kline）：**

```python
async def _collect_daily_kline(task_id: int, params: dict):
    days = params.get("days", 7)
    redis = get_redis()

    # 1. 读取所有上市股票
    async with AsyncSessionLocal() as session:
        symbols = await _get_all_symbols(session)

    # 2. 更新 Redis 总数
    await redis.hset(f"collect:progress:{task_id}", mapping={
        "total": len(symbols), "done": 0, "success": 0, "fail": 0,
        "status": "running", "current": "",
    })
    await redis.expire(f"collect:progress:{task_id}", 86400)

    # 3. 逐批采集
    fetcher = TushareFetcher(KlineBO)
    success = fail = 0
    batch_size = 30

    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i+batch_size]
        async with AsyncSessionLocal() as session:
            svc = KlineAppService(session=session)
            for symbol in batch:
                try:
                    await svc.collect(KlineCollectRequest(symbol=symbol, days=days), fetcher)
                    success += 1
                    detail_status = "success"
                except Exception as e:
                    fail += 1
                    detail_status = "failed"

                # 更新 Redis 进度
                await redis.hset(f"collect:progress:{task_id}", mapping={
                    "done": success + fail,
                    "success": success,
                    "fail": fail,
                    "current": symbol,
                })
            await session.commit()

        # Tushare 限频
        if i + batch_size < len(symbols):
            await asyncio.sleep(1)

    # 4. 写最终结果到 PostgreSQL
    async with AsyncSessionLocal() as session:
        task = await session.get(SysCollectTaskDB, task_id)
        task.status = "success" if fail == 0 else "failed" if success == 0 else "success"
        task.success_count = success
        task.fail_count = fail
        task.finished_at = datetime.now(timezone.utc)
        task.duration_ms = int((task.finished_at - task.started_at).total_seconds() * 1000)
        task.message = f"完成: 成功 {success}, 失败 {fail}"
        await session.commit()

    # 5. 更新 Redis 最终状态
    await redis.hset(f"collect:progress:{task_id}", "status", "success")
```

### 2.5 Redis 接入

已有 Redis 连接配置。需要新增 `get_redis()` 工具函数（如果没有的话），用 `aioredis` / `redis.asyncio`。

```python
from redis.asyncio import Redis

_redis: Redis | None = None

async def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis
```

### 2.6 清理旧的 collect/all 接口

实现完成后，删除 `kline.py` 中的：
- `_collect_all_running` 全局变量
- `_collect_all_progress` 全局字典
- `_bg_collect_all()` 函数
- `POST /klines/collect/all` 路由
- `GET /klines/collect/all/progress` 路由

统一到 `POST /collect/tasks` + `GET /collect/tasks/{id}/progress`。

同时更新 `StockInfoList.vue` 中的"采集日K"按钮，改为跳转到数据采集页面。

## 三、前端实现

### 3.1 页面结构

**文件：** `frontend/src/views/data-collect/DataCollect.vue`

```
PageWrapper
├─ #title: "数据采集"
├─ #toolbar: (无搜索，预留)
└─ 主体
    ├─ CollectPanel.vue   ← 操作面板（上半部分）
    │   ├─ 日K线采集卡片
    │   │   ├─ "更新今日" 按钮 (days=1)
    │   │   ├─ "增量7天" 按钮 (days=7)
    │   │   └─ "自定义范围" → 日期选择器 + 启动
    │   ├─ 估值同步卡片
    │   │   ├─ "同步今日" 按钮
    │   │   └─ "同步近N天" → 天数选择 + 启动
    │   ├─ 股票信息同步卡片
    │   │   └─ "全量同步" 按钮
    │   └─ (后续扩展: 财报/资金流向/融资融券)
    │
    ├─ TaskProgress.vue   ← 当前运行中任务进度（中部）
    │   ├─ 进度条 (done/total)
    │   ├─ 成功/失败/跳过计数
    │   ├─ 当前处理: symbol
    │   ├─ 已用时间
    │   └─ "取消" 按钮
    │
    └─ TaskHistory.vue    ← 历史任务列表（下半部分）
        ├─ el-table
        │   ├─ 任务类型 (tag)
        │   ├─ 触发方式 (手动/定时)
        │   ├─ 参数摘要
        │   ├─ 状态 (tag: 绿成功/红失败/蓝运行中)
        │   ├─ 进度 (success/fail/total)
        │   ├─ 耗时
        │   ├─ 开始时间
        │   └─ 结果摘要
        └─ 分页器
```

### 3.2 路由与菜单

**router/home.ts 新增：**

```typescript
{
  path: 'data-collect',
  name: 'DataCollect',
  component: () => import('@/views/data-collect/DataCollect.vue'),
  meta: { title: '数据采集', icon: 'upload' },
}
```

**LeftBar.vue menuItems 新增：**

```typescript
{ path: '/home/data-collect', title: '数据采集', icon: Upload },
```

菜单顺序建议：数据大盘 → 股票信息 → 操作池 → **数据采集**

### 3.3 API 定义

**文件：** `frontend/src/views/data-collect/api.ts`

```typescript
/** 创建采集任务 */
export interface CreateTaskRequest {
  task_type: 'daily_kline' | 'daily_basic' | 'stock_basic' | 'fin_report'
  params?: Record<string, any>
}

export interface CollectTask {
  id: number
  task_type: string
  trigger_type: string
  params: Record<string, any> | null
  status: string
  total_count: number
  success_count: number
  fail_count: number
  skip_count: number
  started_at: string | null
  finished_at: string | null
  duration_ms: number | null
  message: string | null
  created_at: string
}

export interface TaskProgress {
  total: number
  done: number
  success: number
  fail: number
  skip: number
  status: string
  current: string
  percent: number
  elapsed_ms: number
}

export const createTask = (body: CreateTaskRequest) =>
  http.post<{ task_id: number; total_count: number; message: string }>(
    '/collect/tasks', body
  ).then(unwrap)

export const listTasks = (params?: { task_type?: string; page?: number; page_size?: number }) =>
  http.get<PaginatedResponse<CollectTask>>('/collect/tasks', { params }).then(unwrap)

export const getTaskProgress = (taskId: number) =>
  http.get<TaskProgress>(`/collect/tasks/${taskId}/progress`).then(unwrap)

export const cancelTask = (taskId: number) =>
  http.post(`/collect/tasks/${taskId}/cancel`).then(unwrap)
```

### 3.4 CollectPanel 操作面板设计

用 `el-card` + `el-row` + `el-col` 布局，每种采集类型一个卡片：

```
┌─ 日K线采集 ─────────────────────────────────────────┐
│                                                      │
│  [更新今日]  [增量7天]  [增量30天]                   │
│                                                      │
│  自定义: [开始日期] ~ [结束日期]  [开始采集]         │
│                                                      │
│  上次采集: 2026-09-18 09:30 | 成功 5320 | 耗时 4m   │
└──────────────────────────────────────────────────────┘

┌─ 日频估值 ──────────────┐  ┌─ 股票基本信息 ─────────┐
│                          │  │                         │
│  [同步今日] [同步近3天]  │  │  [全量同步]             │
│                          │  │                         │
│  上次: 09-18 | 15423条   │  │  上次: 09-15 | 5326只   │
└──────────────────────────┘  └─────────────────────────┘
```

### 3.5 TaskProgress 进度展示

运行中任务时显示：

```
┌─ 正在执行: 日K线采集 ────────────────────────────────┐
│                                                      │
│  ████████████████░░░░░░░░░░░░░  45.2%  (2407/5326)  │
│                                                      │
│  ✅ 成功 2400  ❌ 失败 7  ⏭ 跳过 0                  │
│  📌 当前: 002415    ⏱ 已用: 2分30秒                  │
│                                                      │
│                                  [取消采集]           │
└──────────────────────────────────────────────────────┘
```

无运行中任务时隐藏此区域。

### 3.6 TaskHistory 历史记录表

| 任务类型 | 触发 | 参数 | 状态 | 进度 | 耗时 | 开始时间 |
|:---|:---|:---|:---|:---|:---|:---|
| 日K线 | 手动 | 7天 | ✅成功 | 5320/5326 | 4m12s | 09-18 09:30 |
| 日频估值 | 手动 | 3天 | ✅成功 | 15423 | 32s | 09-18 09:25 |
| 日K线 | 定时 | 1天 | ❌失败 | 3200/5326 | 2m05s | 09-17 16:00 |

## 四、StockInfoList.vue 改造

数据采集页面完成后，清理股票列表页：

1. **移除**"采集日K"按钮及相关状态 (`collectingAll`, `collectProgress`, `collectAllHandler`)
2. **移除**"同步估值"按钮及相关状态 (`syncingBasic`, `syncDailyBasicHandler`)
3. **保留**"同步最新数据"按钮（同步股票基本信息，轻量操作，留在列表页合理）
4. 可选：在"同步估值"原位置加一个跳转链接"前往数据采集 →"

## 五、实施步骤

### 第一步：后端基础

1. 创建 ORM 模型 `sys_collect_task.py` + `sys_collect_task_detail.py`
2. 注册到 `models/__init__.py`
3. 生成并执行 Alembic 迁移
4. 创建 Repository `collect_task_repo.py`
5. 创建 Service `collect_task_service.py`
6. 新增 Redis 工具函数（如果没有）

### 第二步：后端路由

1. 创建 `route/api/v1/collect_task.py`
2. 实现 POST/GET 路由
3. 实现后台任务执行器（复用现有 KlineAppService.collect）
4. 注册路由到主 app

### 第三步：前端页面

1. 创建 `views/data-collect/` 目录和组件
2. 创建 `api.ts`
3. 实现 `DataCollect.vue` + 子组件
4. 路由注册 + 菜单添加

### 第四步：清理

1. 删除 `kline.py` 中的旧 collect/all 接口
2. 清理 `StockInfoList.vue` 中的采集相关代码
3. 更新前端 `api.ts` 删除 `collectAllKlines` / `getCollectAllProgress`

### 第五步：验证

1. 手动触发各类型采集，验证进度实时更新
2. 验证任务历史记录正确持久化
3. 验证取消任务功能
4. 验证同类型任务不可重复启动
