# 快速开始指南

**版本**：v4.0  
**日期**：2026年6月  
**技术栈**：Vue-ts + Python LangGraph FastAPI + PostgreSQL pgvector + Redis + Docker

---

## 目录

1. [环境要求](#1-环境要求)
2. [项目初始化](#2-项目初始化)
3. [Docker 一键启动（推荐）](#3-docker-一键启动推荐)
4. [本地开发](#4-本地开发)
5. [第一个分析示例](#5-第一个分析示例)
6. [常见问题](#6-常见问题)

---

## 1. 环境要求

### 1.1 必需环境


| 软件             | 版本      | 说明      |
| -------------- | ------- | ------- |
| Docker         | >= 24   | 容器化（必需） |
| Docker Compose | >= 2.20 | 容器编排    |
| Git            | -       | 代码版本管理  |


### 1.2 可选环境（本地开发需要）


| 软件       | 版本      | 说明    |
| -------- | ------- | ----- |
| Python   | >= 3.11 | 后端开发  |
| Node.js  | >= 20   | 前端开发  |
| npm/pnpm | -       | 前端包管理 |


### 1.3 检查环境

```bash
# 检查 Docker 版本
docker --version
# Docker version 24.x.x

# 检查 Docker Compose 版本
docker-compose --version
# Docker Compose version v2.x.x
```

---

## 2. 项目初始化

### 2.1 克隆项目

```bash
git clone https://github.com/your-org/attribution-analysis.git
cd attribution-analysis
```

### 2.2 目录结构

```
attribution-analysis/
├── backend/                     # Python 后端 (FastAPI)
│   ├── app/
│   │   ├── api/               # API 路由
│   │   ├── models/            # SQLAlchemy 模型
│   │   ├── schemas/           # Pydantic DTO
│   │   ├── services/          # 业务逻辑
│   │   ├── agents/            # LangGraph Agent
│   │   ├── db/                # 数据库连接
│   │   └── cache/             # Redis 缓存
│   ├── scripts/                # 脚本
│   ├── alembic/               # 数据库迁移
│   └── requirements.txt       # 依赖
│
├── frontend/                    # Vue 3 + TypeScript 前端
│   ├── src/
│   │   ├── views/            # 页面
│   │   ├── components/       # 组件
│   │   ├── stores/           # Pinia 状态
│   │   └── api/              # API 调用
│   └── package.json
│
├── docker-compose.yml          # Docker Compose 配置
├── .env.example               # 环境变量示例
└── README.md
```

### 2.3 配置环境变量

```bash
# 复制环境变量文件
cp .env.example .env
```

编辑 `.env` 文件：

```env
# ============ 应用配置 ============
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000

# ============ 数据库 (PostgreSQL) ============
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=attribution
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres123

# ============ Redis ============
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# ============ LLM 配置 (通义千问) ============
LLM_PROVIDER=qianfan
QWEN_API_KEY=sk-your-api-key
QWEN_MODEL=qwen-turbo

# ============ Embedding 配置 ============
EMBEDDING_PROVIDER=qianfan
EMBEDDING_MODEL=text-embedding-v3

# ============ CORS ============
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

---

## 3. Docker 一键启动（推荐）

### 3.1 启动所有服务

```bash
# 启动所有服务（前端、后端、数据库、Redis）
docker-compose up -d

# 查看服务状态
docker-compose ps
```

### 3.2 服务说明

启动后会自动运行：


| 服务         | 端口                                             | 说明              |
| ---------- | ---------------------------------------------- | --------------- |
| Frontend   | [http://localhost](http://localhost)           | Vue 3 前端        |
| Backend    | [http://localhost:8000](http://localhost:8000) | FastAPI 后端      |
| PostgreSQL | localhost:5432                                 | 主数据库 + pgvector |
| Redis      | localhost:6379                                 | 缓存              |


### 3.3 验证服务

```bash
# 健康检查
curl http://localhost:8000/health
```

响应：

```json
{
  "status": "healthy",
  "version": "4.0.0",
  "services": {
    "database": "connected",
    "redis": "connected",
    "pgvector": "connected"
  }
}
```

### 3.4 查看日志

```bash
# 查看后端日志
docker-compose logs -f backend

# 查看前端日志
docker-compose logs -f frontend
```

### 3.5 停止服务

```bash
docker-compose down

# 停止并删除数据卷（慎用）
docker-compose down -v
```

---

## 4. 本地开发

### 4.1 启动基础设施（Docker）

```bash
# 只启动数据库和 Redis
docker-compose up -d postgres rediss
```

### 4.2 后端开发

#### 4.2.1 安装依赖

```bash
cd backend

# 创建虚拟环境 (Windows)
python -m venv venv
.\venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

#### 4.2.2 初始化数据库

```bash
# 运行数据库迁移
alembic upgrade head

# 或者自动迁移
python scripts/init_db.py
```

#### 4.2.3 启动后端

```bash
# 开发模式启动（热重载）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 或者使用 FastAPI 自动生成
fastapi dev app/main.py --port 8000
```

后端启动成功后会看到：

```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Database connected
INFO:     Redis connected
INFO:     pgvector extension enabled
INFO:     Application startup complete.
```

#### 4.2.4 验证后端

```bash
# 健康检查
curl http://localhost:8000/health

# 访问 API 文档
# http://localhost:8000/docs
# http://localhost:8000/redoc
```

### 4.3 前端开发

#### 4.3.1 安装依赖

```bash
cd frontend

# 使用 npm
npm install

# 或使用 pnpm（更快）
pnpm install
```

#### 4.3.2 启动前端

```bash
npm run dev
# 或
pnpm dev
```

前端启动成功后会看到：

```
VITE v5.x.x  ready in 500 ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
```

#### 4.3.3 访问前端

打开浏览器访问 [http://localhost:5173](http://localhost:5173)

---

## 5. 第一个分析示例

### 5.1 采集股票数据

```bash
# 采集单只股票（贵州茅台）
curl -X POST http://localhost:8000/api/v1/klines/collect \
  -H "Content-Type: application/json" \
  -d '{"symbol": "600519", "period": "daily", "start_date": "2024-01-01"}'
```

响应：

```json
{
  "success": true,
  "data": {
    "symbol": "600519",
    "records_collected": 365,
    "date_range": {
      "start": "2024-01-01",
      "end": "2024-12-31"
    }
  }
}
```

### 5.2 查询 K 线数据

```bash
# 获取 K 线数据
curl "http://localhost:8000/api/v1/klines?symbol=600519&start_date=2024-06-01&end_date=2024-06-25"
```

### 5.3 获取技术指标

```bash
# 获取技术指标
curl "http://localhost:8000/api/v1/indicators?symbol=600519&date=2024-06-25&indicators=ma,ema,rsi"
```

响应：

```json
{
  "success": true,
  "data": {
    "symbol": "600519",
    "date": "2024-06-25",
    "indicators": {
      "ma5": 1680.50,
      "ma10": 1675.20,
      "ma20": 1668.30,
      "ema12": 1685.40,
      "ema26": 1672.10,
      "rsi": 58.5
    }
  }
}
```

### 5.4 发起分析

```bash
# 发起归因分析
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "600519",
    "trade_date": "2024-06-25",
    "include_news": true
  }'
```

响应：

```json
{
  "success": true,
  "data": {
    "id": "analysis_20240625_001",
    "status": "completed",
    "created_at": "2024-06-25T10:00:00Z",

    "anomaly": {
      "is_anomaly": true,
      "score": 0.85,
      "methods": [
        {
          "name": "rsi",
          "result": true,
          "value": 58.5,
          "threshold": 70,
          "description": "RSI 进入超买区域"
        }
      ],
      "signal": {
        "direction": "down",
        "velocity": -0.02,
        "inflection": true
      }
    },

    "sentiment": {
      "label": "negative",
      "score": -0.3,
      "news_count": 5,
      "key_events": ["业绩预期下调", "资金流出"]
    },

    "attribution": {
      "top_drivers": ["北向资金净流出", "板块轮动"],
      "top_draggers": [],
      "conclusion": "茅台下跌主要由资金面因素驱动"
    },

    "experience": {
      "matched": {
        "id": 123,
        "similarity": 0.87,
        "confidence": 0.82,
        "conclusion": "2024-03-15 类似情况，当时原因是..."
      },
      "is_reused": true
    },

    "report": {
      "summary": "贵州茅台今日出现调整，RSI 指标显示超买，短期资金面偏紧",
      "insights": [
        "北向资金连续净流出是主要拖累因素",
        "与历史相似案例匹配度 87%，参考历史走势"
      ],
      "suggestions": [
        "建议关注北向资金动向",
        "等待 RSI 回落至合理区间"
      ]
    }
  }
}
```

### 5.5 提交反馈

```bash
# 提交用户反馈
curl -X POST http://localhost:8000/api/v1/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "analysis_id": "analysis_20240625_001",
    "experience_id": 123,
    "is_helpful": true,
    "rating": 5,
    "comment": "分析准确，与实际情况吻合"
  }'
```

---

## 6. 常见问题

### 6.1 数据库连接失败

**错误**：`Connection refused to localhost:5432`

**解决**：

```bash
# 检查 PostgreSQL 是否运行
docker ps | grep postgres

# 启动 PostgreSQL
docker-compose up -d postgres

# 测试连接
docker exec -it attribution-postgres pg_isready -U postgres
```

### 6.2 Redis 连接失败

**错误**：`Failed to connect to Redis`

**解决**：

```bash
# 检查 Redis 是否运行
docker ps | grep redis

# 启动 Redis
docker-compose up -d redis

# 测试连接
docker exec -it attribution-redis redis-cli ping
```

### 6.3 pgvector 扩展未启用

**错误**：`extension "vector" not found`

**解决**：

```bash
# 在 PostgreSQL 容器中执行
docker exec -it attribution-postgres psql -U postgres -d attribution -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 6.4 通义千问 API 密钥无效

**错误**：`Invalid API key`

**解决**：

1. 访问 [https://qianfan.ai/console/apikey](https://qianfan.ai/console/apikey)
2. 创建新的 API Key
3. 更新 `.env` 中的 `QWEN_API_KEY`
4. 重启后端服务

```bash
docker-compose restart backend
```

### 6.5 前端无法访问后端 API

**错误**：`CORS error`

**解决**：

1. 确认后端 `CORS_ORIGINS` 配置正确
2. 检查前端 `VITE_API_BASE_URL` 配置

```env
# backend/.env
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### 6.6 依赖安装失败

**Python 依赖**：

```bash
cd backend

# 清理缓存
rm -rf venv
pip cache purge

# 重新安装
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

**前端依赖**：

```bash
cd frontend

# 清理缓存
rm -rf node_modules pnpm-lock.yaml package-lock.json

# 重新安装
pnpm install
```

### 6.7 端口被占用

**错误**：`EADDRINUSE: address already in use`

**解决**：

```bash
# Windows - 查找占用端口的进程
netstat -ano | findstr :8000

# 结束进程
taskkill /PID <PID> /F
```

### 6.8 Docker 构建失败

**解决**：

```bash
# 清理 Docker 缓存
docker system prune -a

# 重新构建
docker-compose build --no-cache
docker-compose up -d
```

---

## 7. 下一步

- 阅读 [架构文档](./architecture.md) 了解系统设计
- 阅读 [API 文档](./api.md) 了解接口详情
- 阅读 [部署指南](./deployment.md) 了解生产部署
- 阅读 [数据源说明](./data-source.md) 了解 AkShare 接入

---

## 技术支持

- 提交 Issue：[https://github.com/your-org/attribution-analysis/issues](https://github.com/your-org/attribution-analysis/issues)
- 文档更新：欢迎提交 PR 完善文档

