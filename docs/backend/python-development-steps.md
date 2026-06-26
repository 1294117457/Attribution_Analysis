# Python 后端开发 — 简明步骤

> 本文档：快速开始，只需按顺序执行每一步
> 详细说明：参考 `docs/backend/python-development-steps.md`

---

## 第一步：安装 Python 环境

**做什么：** 安装 Python 并验证

```bash
# Windows: https://www.python.org/downloads/
# Linux/Mac: 通常已预装
python --version
pip --version
```

**目的：** 确保系统有 Python 运行环境

---

## 第二步：pip 换源（国内加速）

**做什么：** 把 pip 的下载源换成清华镜像

```bash
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

**目的：** 国内访问 PyPI 下载更快，避免超时

---

## 第三步：创建虚拟环境

**做什么：** 新建一个隔离的项目环境

```bash
cd backend
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

**目的：** 每个项目用独立的依赖包，互不干扰

---

## 第四步：安装依赖包

**做什么：** 安装本项目需要的全部第三方库

```bash
pip install fastapi uvicorn sqlalchemy asyncpg alembic \
    akshare pandas pydantic-settings redis httpx
```

**目的：** 为项目提供 Web 框架、数据库操作、数据采集等能力

---

## 第五步：配置环境变量

**做什么：** 在 `backend/.env` 文件中写入数据库连接信息

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/attribution
DATABASE_URL_ASYNC=postgresql+asyncpg://postgres:postgres@localhost:5432/attribution
REDIS_URL=redis://localhost:6379/0
```

**目的：** 把敏感信息和配置集中管理，不用硬编码在代码里

---

## 第六步：启动 PostgreSQL 数据库

**做什么：** 用 Docker 启动一个 PostgreSQL 数据库容器

```bash
docker run -d --name attribution-postgres \
  -e POSTGRES_DB=attribution \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```

**目的：** 为项目提供一个可以存储股票数据的数据库

---

## 第七步：初始化数据库表结构

**做什么：** 让 Alembic 根据模型定义自动创建数据表

```bash
cd backend
alembic upgrade head
```

**目的：** 在数据库中创建 `stock_klines` 等数据表

---

## 第八步：启动后端服务

**做什么：** 启动 FastAPI 应用

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**目的：** 让后端服务运行起来，提供 API 接口

---

## 第九步：验证服务正常运行

**做什么：** 访问健康检查接口

浏览器打开：http://localhost:8000/health

预期返回：`{"status": "ok"}`

**目的：** 确认服务启动成功

---

## 第十步：采集股票数据（可选）

**做什么：** 采集一只股票的历史 K 线数据

```bash
python -m scripts.collect_data 600519
```

**目的：** 把数据从 AkShare 拉取并存入数据库

---

## 第十一步：查询数据（可选）

**做什么：** 通过 API 查询已存储的数据

```bash
curl "http://localhost:8000/api/v1/klines?symbol=600519&start_date=2024-01-01&end_date=2024-06-25"
```

**目的：** 验证数据是否正确存储、API 是否正常工作

---

## 完成后的项目结构

```
backend/
├── app/
│   ├── main.py           # 入口（第六步创建）
│   ├── config.py         # 配置（第五步相关）
│   ├── models/kline.py   # 数据模型（第七步自动创建）
│   ├── schemas/kline.py  # 数据格式定义
│   ├── services/collector.py  # 数据采集逻辑
│   └── api/v1/klines.py # API 路由
├── scripts/
│   └── collect_data.py   # 采集脚本（第十步用到）
├── alembic/              # 数据库迁移
└── .env                  # 环境变量（第五步创建）
```

---

## 快速命令速查

| 操作 | 命令 |
|------|------|
| 启动数据库 | `docker start attribution-postgres` |
| 启动服务 | `uvicorn app.main:app --reload --port 8000` |
| 采集数据 | `python -m scripts.collect_data <股票代码>` |
| 查看 API 文档 | http://localhost:8000/docs |
| 迁移数据库 | `alembic upgrade head` |
