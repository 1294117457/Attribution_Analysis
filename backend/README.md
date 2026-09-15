# 智能金融数据归因分析平台 - 后端

> 基于 **DDD（领域驱动设计）** 架构的金融数据后端服务。

## 架构

采用 DDD 分层架构，从内到外依次为：

```
路由层 (route/)
    ↓
应用层 (application/)
    ↓
领域层 (domain/)
    ↓
基础设施层 (infrastructure/)
```

### 依赖方向

```
route  ──→  application  ──→  domain  ←──  infrastructure
                                       ↑
                                (实现 domain 定义的 Repository 接口)
```

- **路由层**：HTTP 请求/响应、参数校验
- **应用层**：用例编排、事务边界、调用仓储/采集器
- **领域层**：业务实体、值对象、领域规则（不依赖任何外部框架）
- **基础设施层**：ORM 模型、数据库连接、外部数据采集、仓储实现

## 目录结构

```
backend/
├── src/
│   ├── main.py                    # FastAPI 应用入口
│   ├── dependencies.py            # 项目级依赖
│   │
│   ├── domain/                    # ⭐ 领域层（DDD 核心）
│   │   ├── base.py                # Entity、AggregateRoot、ValueObject
│   │   ├── kline/
│   │   │   ├── entity.py          # Kline 聚合根
│   │   │   ├── value_objects.py   # StockCode、TradeDate
│   │   │   ├── schemas.py         # KlineBO、KlineVO
│   │   │   ├── events.py          # 领域事件
│   │   │   └── repository.py      # 仓储接口（抽象）
│   │   └── stock_info/
│   │       ├── entity.py
│   │       ├── value_objects.py
│   │       ├── schemas.py
│   │       └── repository.py
│   │
│   ├── application/               # ⭐ 应用层（用例编排）
│   │   ├── kline_service.py       # K线应用服务
│   │   ├── stock_service.py       # 股票应用服务
│   │   ├── exceptions.py          # 应用层异常
│   │   └── dto/                   # 请求/响应 DTO
│   │
│   ├── infrastructure/            # ⭐ 基础设施层
│   │   ├── config.py              # 配置（pydantic-settings）
│   │   ├── database/              # 数据库连接、ORM 模型
│   │   ├── repositories/          # 仓储实现
│   │   └── collectors/            # ACL 防腐层（AkShare）
│   │
│   └── route/                     # ⭐ 路由层
│       ├── api/v1/
│       │   ├── kline.py           # K线 API
│       │   └── stock.py           # 股票 API
│       └── schemas/response.py    # 统一响应格式
│
└── tests/                         # 单元测试
    ├── test_domain.py             # 领域层测试
    ├── test_application.py        # 应用层测试
    └── test_api.py                # API 集成测试
```

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置数据库

修改 `.env` 文件：

```ini
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname
```

### 启动服务

```bash
PYTHONPATH=src python src/main.py
# 或
PYTHONPATH=src uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

访问：
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

### 运行测试

```bash
PYTHONPATH=src pytest tests/ -v
```

## API 端点

### 健康检查
- `GET /health`

### K线相关
- `GET /api/v1/klines/{symbol}` - 查询K线
- `GET /api/v1/klines/{symbol}/stats` - K线统计
- `GET /api/v1/klines/{symbol}/{trade_date}` - 查询单条K线
- `POST /api/v1/klines/collect` - 采集K线
- `POST /api/v1/klines/collect/batch` - 批量采集K线
- `DELETE /api/v1/klines/{symbol}` - 删除全部K线
- `DELETE /api/v1/klines/{symbol}/{trade_date}` - 删除单条K线

### 股票相关
- `GET /api/v1/stocks/` - 股票列表
- `GET /api/v1/stocks/{symbol}` - 股票详情
- `POST /api/v1/stocks/` - 新增/更新股票
- `PATCH /api/v1/stocks/{symbol}` - 部分更新股票
- `DELETE /api/v1/stocks/{symbol}` - 删除股票

## 统一响应格式

```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

- `code = 200`：成功
- `code = 201`：创建成功
- `code = 400`：参数错误
- `code = 404`：资源不存在
- `code = 422`：参数校验失败
- `code = 500`：服务器错误
- `code = 502`：网关错误（外部数据源失败）

## 重构历史

- Phase 1：`app/` + `data/` + `infra/` 分层
- Phase 2：DDD 架构（本版本）
  - 新增 `domain/` 领域层
  - 重命名 `interfaces/` → `route/`
  - 应用层使用 `async/await`
  - 数据采集抽象为 ACL 防腐层

详见 `docs/02/step2/` 目录。
