# Phase 1 开发文档索引

> K线数据采集 + 技术指标计算 + REST API + 前端可视化

---

## 文档列表

| 文件 | 内容 | 对应代码目录 |
|------|------|------------|
| [01-infra.md](./01-infra.md) | 基础设施层：数据库连接、配置、Mixin | `src/infra/` |
| [02-collectors.md](./02-collectors.md) | 数据采集层：接口协议、AkShare 适配器、Parser | `src/collectors/` |
| [03-model-repo.md](./03-model-repo.md) | 持久层：ORM 模型、数据访问层（Repo） | `kline/model.py` `kline/repo.py` `stock_info/...` |
| [04-schema.md](./04-schema.md) | 数据结构：BO/DTO/VO 定义、统一响应格式 | 各域 `schema.py` + `app/response.py` |
| [05-service.md](./05-service.md) | 业务逻辑层：采集编排、查询、指标 | 各域 `service.py` |
| [06-router-app.md](./06-router-app.md) | 路由层 + 应用入口：API 端点、main.py、异常处理 | 各域 `router.py` + `app/main.py` |
| [07-indicators.md](./07-indicators.md) | 技术指标计算：MA/MACD/RSI（pandas） | `src/indicators/calculator.py` |

---

## 目标目录结构（Phase 1 完成后）

```
backend/src/
├── app/
│   ├── main.py
│   ├── dependencies.py
│   ├── response.py
│   └── handlers/
│       └── __init__.py
│
├── infra/
│   ├── config.py
│   └── database/
│       ├── base.py
│       ├── connection.py
│       └── mixins.py
│
├── collectors/
│   ├── collector.py
│   ├── interfaces/
│   │   └── fetcher.py
│   └── akshare/
│       ├── fetcher.py
│       └── parser.py
│
├── kline/
│   ├── model.py
│   ├── schema.py
│   ├── repo.py
│   ├── service.py
│   └── router.py
│
├── stock_info/
│   ├── model.py
│   ├── schema.py
│   ├── repo.py
│   ├── service.py
│   └── router.py
│
└── indicators/
    ├── calculator.py
    ├── schema.py
    ├── service.py
    └── router.py
```

---

## 开发顺序建议

按以下顺序开发，每步可独立验证：

```
Step 1  infra/               数据库连接测试（test_db.py）
Step 2  kline/model.py       建表验证
Step 3  collectors/          单独测试采集（test_collect.py）
Step 4  kline/repo.py        单独测试 save_batch + query
Step 5  kline/service.py     集成测试采集+存储
Step 6  kline/router.py      启动 uvicorn，Swagger 验证接口
Step 7  stock_info/ 域        同上
Step 8  indicators/           验证指标计算结果
Step 9  前端对接              axios 对接 + ECharts 渲染
```

---

## API 端点速览

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/api/stocks/` | 股票列表 + K线统计 |
| GET | `/api/stocks/{symbol}` | 股票详情 |
| POST | `/api/klines/collect` | 采集K线（AkShare） |
| GET | `/api/klines/{symbol}` | 查询K线（支持日期范围） |
| DELETE | `/api/klines/{symbol}` | 删除股票全部K线 |
| DELETE | `/api/klines/{symbol}/{date}` | 删除单条K线 |
| GET | `/api/indicators/{symbol}` | 技术指标（MA/MACD/RSI） |

---

## 依赖安装

```bash
pip install fastapi uvicorn[standard] sqlalchemy asyncpg pydantic-settings akshare pandas
```

```bash
# 启动
uvicorn src.app.main:app --reload --port 8000
```

---

## 分层职责一句话总结

| 层 | 一句话职责 | 允许做 | 禁止做 |
|----|-----------|--------|--------|
| `router` | 接参数、调Service、返响应 | 参数校验、权限判断 | try/except、写SQL、调外部API |
| `service` | 编排业务流程 | 调Repo、调Collector | 写SQL、直接操作db |
| `repo` | SQL 读写 | select/insert/update/delete | 业务规则、调外部API |
| `collector` | 拉外部数据 | 调AkShare/Tushare、格式转换 | 操作数据库、业务规则 |
| `infra` | 基础能力 | DB连接、配置读取 | 任何业务逻辑 |
