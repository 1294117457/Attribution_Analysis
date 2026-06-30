##### 1.总体架构

```
基于docker compose的微服务模式，
	后期可升级k8s编排
布局分为
	nginx网关、frontend，backend，agent，postgreSql，qdrant，redis
```

##### 2.backend

```
fastApi
	接收、持久化、处理数据
	涨跌幅计算、MA/EMA，3σ/IQR，同环比偏差、拐点检测
langgraph
	新闻情感分析，机器学习预测，经验积累
	LLM 生成自然语言报告
```

##### 3.**Persistence**

```
PostgreSql+pgvector

docker run -d --name attribution-postgres \
  -e POSTGRES_DB=attribution \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=zhouchenhui \
  -p 5432:5432 \
  -v /home/project/postgre/data:/var/lib/postgresql/data \
  --restart unless-stopped \
  pgvector/pgvector:pg16 \
  -c 'listen_addresses=*' \
  -c 'max_connections=100'
  
  容器 (attribution-postgres)
│
├── PostgreSQL 16 + pgvector 扩展
│   ├── 数据目录: /var/lib/postgresql/data (挂载到宿主机)
│   ├── 配置文件: /var/lib/postgresql/data/postgresql.conf
│   ├── 认证配置: /var/lib/postgresql/data/pg_hba.conf
│   └── 数据库文件: /var/lib/postgresql/data/base/
│
├── 数据库 (attribution)  ← 你创建的数据库
│   ├── 默认 Schema: public
│   ├── 系统表: pg_catalog, information_schema
│   └── (你后续会创建的表: stock_klines, ...)
│
├── 系统数据库 (自动创建)
│   ├── postgres      ← 默认管理数据库
│   ├── template0     ← 模板库（只读）
│   └── template1     ← 模板库（可修改）
│
└── 用户 (postgres)   ← 超级用户
```

```
整体还是一个postgre数据库，只是带了pgvector扩展
然后内部数据表可以带embedding字段

DATABASE_URL=postgresql://postgres:zhouchenhui@223.109.49.63:5432/attribution
DATABASE_URL_ASYNC=postgresql+asyncpg://postgres:zhouchenhui@223.109.49.63:5432/attribution
REDIS_URL=redis://localhost:6379/0
```

```
建议按这个顺序来：

app/config.py — 读取 .env 配置
app/db/database.py — 创建数据库引擎
app/db/session.py — 数据库会话管理
app/models/base.py — SQLAlchemy Base 类
app/models/kline.py — K 线数据模型（定义表结构）
app/main.py — FastAPI 入口，先写个 /health 接口
启动 uvicorn app.main:app --reload 验证能跑起来
alembic init alembic — 初始化 alembic
修改 alembic/env.py — 导入你的模型
alembic revision --autogenerate -m "create klines table" — 自动生成迁移
alembic upgrade head — 建表
app/schemas/kline.py — Pydantic 请求/响应模型
app/services/ — 业务逻辑
app/api/v1/klines.py — API 路由
scripts/collect_data.py — 数据采集脚本
```

##### redis

```
docker run -d --name attribution-redis \
  -e REDIS_PASSWORD=zhouchenhui \
  -p 6379:6379 \
  -v /home/project/redis/data:/data \
  --restart unless-stopped \
  redis:7.2-alpine \
  redis-server --requirepass zhouchenhui --appendonly yes
```

##### architecture

```
app/
├── models/                      # 业务模型（Stock, User 等）
│   ├── __init__.py
│   ├── stock.py
│   └── user.py
│
├── langgraph/                   # LangGraph 专用
│   ├── __init__.py
│   ├── state.py                # State 定义
│   ├── models.py               # LangGraph 专用模型（输入/输出/结果）
│   ├── graph.py                # 图定义
│   ├── config.py               # LLM 配置
│   └── nodes/                  # 节点实现
│       ├── __init__.py
│       ├── retrieve.py
│       ├── analyze.py
│       ├── report.py
│       └── tools.py
│
├── services/
├── api/
└── main.py
```

结合ML,RAG

```
backend/
│
├── core/                    # 核心共享层
│   ├── __init__.py
│   ├── config.py
│   ├── types.py
│   └── models/
│
├── app/                    # API 应用层
│   ├── __init__.py
│   ├── main.py
│   ├── api/
│   ├── schemas/
│   ├── database/
│   ├── services/
│   └── scripts/            # app 专用脚本
│
├── data/                   # 数据采集层
│   ├── __init__.py
│   ├── fetchers/
│   ├── collectors/
│   ├── parsers/
│   └── scripts/            # data 专用脚本
│
├── ml/                    # 机器学习层
│   ├── __init__.py
│   ├── predictor/
│   ├── detector/
│   ├── classifier/
│   ├── features/
│   └── scripts/            # ml 专用脚本
│
├── rag/                   # RAG 层
│   ├── __init__.py
│   ├── embeddings/
│   ├── vector_store/
│   ├── knowledge_base.py
│   └── scripts/            # rag 专用脚本
│
├── graph/                 # Graph 编排层
│   ├── __init__.py
│   ├── models/
│   ├── agent/
│   ├── tools/
│   ├── nodes/
│   └── workflows/
│
└── tests/                 # 测试
    ├── test_app/
    ├── test_data/
    ├── test_ml/
    ├── test_rag/
    └── test_graph/
```

## 文档索引

详细开发文档位于 `docs/backend/` 目录：

### ✅ 已完成
- [core 模块开发步骤](./backend/core/step/01_create_core.md)
- [core 模块设计分析](./backend/core/analysis/01_core_design.md)
- [app 模块开发步骤](./backend/app/step/01_create_app.md)
- [app 模块设计分析](./backend/app/analysis/01_app_design.md)
- [data 模块开发步骤](./backend/data/step/01_create_data.md)
- [data 模块设计分析](./backend/data/analysis/01_data_design.md)
- [ml 模块开发步骤](./backend/ml/step/01_create_ml.md)
- [ml 异常检测开发步骤](./backend/ml/step/01_create_detector.md)
- [ml 模块设计分析](./backend/ml/analysis/01_ml_design.md)
- [ml 异常检测设计分析](./backend/ml/analysis/01_detector_design.md)

### ⏳ 待开发
- rag 模块
- graph 模块

### 开发顺序
1. **core** → 配置和类型
2. **app** → FastAPI 骨架
3. **data** → 数据采集
4. **ml/detector** → 异常检测 ✅
5. ml/classifier → 情感分析
6. ml/predictor → 价格预测
7. rag → 知识检索
8. graph → 工作流编排

