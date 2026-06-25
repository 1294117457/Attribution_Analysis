# Attribution Analysis Backend

Python FastAPI 后端，用于智能金融数据归因分析平台。

## 技术栈

- **FastAPI** - 现代高性能 Web 框架
- **SQLAlchemy** - Python ORM
- **AkShare** - A股数据接口
- **LangGraph** - AI Agent 编排
- **MySQL** - 关系数据库
- **Qdrant** - 向量数据库（经验系统）

## 快速开始

### 1. 创建虚拟环境

```bash
cd backend
python -m venv venv

# Windows
.\venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，配置数据库连接
```

### 4. 初始化数据库

```bash
# 运行迁移
alembic upgrade head
```

### 5. 启动服务

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. 访问 API 文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 项目结构

```
backend/
├── app/
│   ├── api/          # API 路由
│   ├── models/       # 数据库模型
│   ├── schemas/      # Pydantic 模型
│   ├── services/     # 业务逻辑
│   ├── db/           # 数据库连接
│   ├── agents/       # LangGraph Agent
│   └── tasks/        # 定时任务
├── tests/            # 测试
├── scripts/          # 脚本
└── alembic/          # 数据库迁移
```

## 环境变量说明

| 变量 | 说明 | 默认值 |
|------|------|--------|
| DATABASE_URL | MySQL 连接字符串 | mysql+pymysql://root:password@localhost:3306/attribution_db |
| DEBUG | 调试模式 | True |
| REDIS_URL | Redis 连接 | redis://localhost:6379/0 |
| QDRANT_URL | Qdrant 地址 | http://localhost:6333 |
| DASHSCOPE_API_KEY | 通义千问 API Key | - |

## 常用命令

```bash
# 安装依赖
pip install -r requirements.txt

# 运行迁移
alembic revision --autogenerate -m "描述"
alembic upgrade head

# 启动服务
uvicorn app.main:app --reload

# 运行测试
pytest

# 代码格式化
black .
```
