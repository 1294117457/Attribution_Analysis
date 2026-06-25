# 快速开始指南

**版本**：v2.0  
**日期**：2026年6月

---

## 目录

1. [环境要求](#1-环境要求)
2. [项目初始化](#2-项目初始化)
3. [后端开发环境](#3-后端开发环境)
4. [前端开发环境](#4-前端开发环境)
5. [一键启动](#5-一键启动)
6. [第一个分析示例](#6-第一个分析示例)
7. [常见问题](#7-常见问题)

---

## 1. 环境要求

### 1.1 必需环境

| 软件 | 版本 | 说明 |
|------|------|------|
| Node.js | >= 20.0.0 | 建议使用 LTS 版本 |
| pnpm | >= 8.0.0 | 包管理器（更快） |
| PostgreSQL | >= 15 | 数据库 |
| Docker | >= 24 | 容器化（可选） |

### 1.2 检查环境

```bash
# 检查 Node.js 版本
node --version
# v20.x.x

# 检查 pnpm 版本
pnpm --version
# 8.x.x

# 检查 Docker（可选）
docker --version
# Docker version 24.x.x
```

### 1.3 安装 pnpm

```bash
npm install -g pnpm
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
├── backend/              # Node.js 后端
├── frontend/             # Vue 3 前端
├── docker-compose.yml    # Docker 配置
└── .env.example          # 环境变量示例
```

### 2.3 安装依赖

```bash
# 安装后端依赖
cd backend
pnpm install

# 安装前端依赖
cd ../frontend
pnpm install
```

---

## 3. 后端开发环境

### 3.1 配置环境变量

```bash
# 复制环境变量文件
cd backend
cp .env.example .env
```

编辑 `.env` 文件：

```env
# 应用配置
NODE_ENV=development
PORT=3000

# 数据库
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/attribution

# 向量数据库 (Qdrant)
VECTOR_DB_URL=http://localhost:6333
VECTOR_DB_COLLECTION=experiences

# LLM 配置 (OpenAI)
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-api-key
OPENAI_MODEL=gpt-4o-mini

# LLM 配置 (通义千问，可选)
# QWEN_API_KEY=sk-your-api-key

# JWT
JWT_SECRET=your-super-secret-jwt-key
JWT_EXPIRES_IN=7d

# CORS
CORS_ORIGIN=http://localhost:5173
```

### 3.2 启动 PostgreSQL

**方式一：使用 Docker（推荐）**

```bash
docker run -d \
  --name attribution-postgres \
  -e POSTGRES_DB=attribution \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:16-alpine
```

**方式二：本地安装**

参考 [PostgreSQL 官方安装指南](https://www.postgresql.org/download/)

### 3.3 启动 Qdrant 向量数据库

```bash
docker run -d \
  --name attribution-qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  qdrant/qdrant:latest
```

### 3.4 初始化数据库

```bash
cd backend

# 生成 Prisma Client
pnpm prisma generate

# 推送数据库 schema
pnpm prisma db push

# 创建初始管理员用户（可选）
pnpm prisma db seed
```

### 3.5 启动后端开发服务器

```bash
cd backend
pnpm dev
```

后端启动成功后会看到：

```
$ fastify start -l info dist/index.js

Server listening at http://localhost:3000
✓ Database connected
✓ Vector DB connected
✓ LangGraph initialized
```

### 3.6 验证后端

```bash
# 健康检查
curl http://localhost:3000/api/health
```

响应：

```json
{
  "status": "healthy",
  "version": "2.0.0",
  "services": {
    "database": "connected",
    "vectorDb": "connected",
    "llm": "available"
  }
}
```

---

## 4. 前端开发环境

### 4.1 配置环境变量

```bash
cd frontend
cp .env.example .env
```

编辑 `.env` 文件：

```env
VITE_API_BASE_URL=http://localhost:3000/api
VITE_APP_TITLE=智能金融归因分析平台
```

### 4.2 启动前端开发服务器

```bash
cd frontend
pnpm dev
```

前端启动成功后会看到：

```
VITE v5.x.x  ready in 500 ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
➜  press h + enter to show help
```

### 4.3 访问前端

打开浏览器访问 http://localhost:5173

---

## 5. 一键启动

### 5.1 使用 Docker Compose（推荐）

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps
```

这将启动：
- PostgreSQL 数据库
- Qdrant 向量数据库
- 后端 API 服务 (http://localhost:3000)
- 前端应用 (http://localhost:5173)

### 5.2 使用 Makefile

```bash
# 安装依赖
make install

# 开发模式启动
make dev

# 生产模式构建
make build

# 一键启动（生产）
make start
```

---

## 6. 第一个分析示例

### 6.1 准备测试数据

创建 `demo.csv` 文件：

```csv
date,region,price,volume
2025-06-01,亚洲,45000,2500000
2025-06-02,亚洲,44800,2600000
2025-06-03,亚洲,44500,2800000
2025-06-04,亚洲,43000,3500000
2025-06-05,亚洲,42000,4000000
2025-06-01,美国,45500,2300000
2025-06-02,美国,45300,2400000
2025-06-03,美国,45000,2550000
2025-06-04,美国,43500,3200000
2025-06-05,美国,42800,3800000
```

### 6.2 上传数据

```bash
curl -X POST http://localhost:3000/api/data/upload \
  -H "Authorization: Bearer <your-token>" \
  -F "file=@demo.csv" \
  -F "name=比特币测试数据" \
  -F "dateColumn=date" \
  -F "metricColumns=price,volume" \
  -F "dimensionColumns=region"
```

响应：

```json
{
  "success": true,
  "data": {
    "id": "ds_20240625_001",
    "name": "比特币测试数据",
    "recordCount": 10
  }
}
```

### 6.3 发起分析

```bash
curl -X POST http://localhost:3000/api/analyze \
  -H "Authorization: Bearer <your-token>" \
  -F "dataSourceId=ds_20240625_001" \
  -F "metric=price" \
  -F "dimensions=region" \
  -F "compareType=PERIOD_OVER_PERIOD"
```

### 6.4 查看分析结果

响应将包含：

- **anomaly**: 异常检测结果
- **attribution**: 归因分析结果
- **report**: AI 生成的分析报告
- **experience**: 匹配的历史经验

### 6.5 提交反馈

```bash
curl -X POST http://localhost:3000/api/feedback \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "analysisId": "analysis_xxx",
    "experienceId": "exp_xxx",
    "isHelpful": true,
    "rating": 5,
    "comment": "分析准确"
  }'
```

---

## 7. 常见问题

### 7.1 数据库连接失败

**错误**：`Connection refused to localhost:5432`

**解决**：

```bash
# 检查 PostgreSQL 是否运行
docker ps | grep postgres

# 启动 PostgreSQL
docker start attribution-postgres

# 或本地检查
pg_isready -h localhost -p 5432
```

### 7.2 向量数据库连接失败

**错误**：`Failed to connect to vector DB`

**解决**：

```bash
# 检查 Qdrant 是否运行
docker ps | grep qdrant

# 启动 Qdrant
docker start attribution-qdrant
```

### 7.3 OpenAI API 密钥无效

**错误**：`Invalid API key`

**解决**：

1. 访问 https://platform.openai.com/api-keys
2. 创建新的 API Key
3. 更新 `backend/.env` 中的 `OPENAI_API_KEY`
4. 重启后端服务

### 7.4 前端无法访问后端 API

**错误**：`CORS error`

**解决**：

1. 确认后端 `CORS_ORIGIN` 配置正确
2. 检查前端 `VITE_API_BASE_URL` 配置

```env
# backend/.env
CORS_ORIGIN=http://localhost:5173
```

```env
# frontend/.env
VITE_API_BASE_URL=http://localhost:3000/api
```

### 7.5 依赖安装失败

**解决**：

```bash
# 清理缓存
rm -rf node_modules pnpm-lock.yaml

# 重新安装
pnpm install
```

### 7.6 Prisma 生成失败

**错误**：`Cannot find Prisma Client`

**解决**：

```bash
cd backend
pnpm prisma generate
pnpm prisma db push
```

### 7.7 端口被占用

**错误**：`EADDRINUSE: address already in use`

**解决**：

```bash
# 查找占用端口的进程
# Windows
netstat -ano | findstr :3000

# 结束进程
taskkill /PID <PID> /F
```

---

## 8. 下一步

- 阅读 [架构文档](./architecture.md) 了解系统设计
- 阅读 [API 文档](./api.md) 了解接口详情
- 阅读 [部署指南](./deployment.md) 了解生产部署

---

## 技术支持

- 提交 Issue：https://github.com/your-org/attribution-analysis/issues
- 文档更新：欢迎提交 PR 完善文档
