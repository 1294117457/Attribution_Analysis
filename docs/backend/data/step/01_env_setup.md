# Step 1: 环境配置

## 1. Python 版本

```bash
python --version
# 推荐 Python 3.10+
```

---

## 2. 创建虚拟环境

```bash
cd backend

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows
```

---

## 3. 安装依赖

### 基础依赖 (requirements.txt)

```
# 文件: backend/requirements.txt

# Web 框架
fastapi==0.115.0
uvicorn[standard]==0.30.6

# 数据库
sqlalchemy==2.0.35
pydantic-settings==2.5.2
psycopg2-binary==2.9.10

# 数据采集
akshare==1.18.64
pandas==2.2.3

# 工具
python-dotenv==1.0.1
```

### 安装

```bash
pip install -r requirements.txt
```

---

## 4. 环境变量配置

### 创建 .env 文件

```bash
cp .env.example .env
```

### .env 内容

```bash
# 文件: backend/.env

# 数据库 (PostgreSQL)
DATABASE_URL=postgresql://postgres:password@localhost:5432/attribution
DATABASE_URL_ASYNC=postgresql+asyncpg://postgres:password@localhost:5432/attribution

# Redis (可选)
REDIS_URL=redis://localhost:6379/0

# API
API_V1_PREFIX=/api/v1
```

---

## 5. 项目结构

```
backend/
├── .env                  # 环境变量 (不要提交到 git)
├── .env.example          # 环境变量模板
├── requirements.txt      # Python 依赖
│
├── app/                  # FastAPI 应用
│   ├── api/             # API 路由
│   ├── database/        # 数据库 (SQLAlchemy ORM)
│   ├── schemas/         # Pydantic 业务模型
│   ├── services/       # 业务逻辑
│   └── main.py          # 应用入口
│
├── core/                 # 核心模块
│   ├── config.py        # 配置管理
│   └── types.py         # 类型定义
│
├── data/                 # 数据采集模块 (重点)
│   ├── akshare_client.py  # AkShare 客户端
│   ├── schemas.py         # 数据模型
│   └── service.py         # 采集服务
│
├── detector/             # 异常检测模块
│
└── tests/               # 测试
```

### 命名规范

| 目录 | 类型 | 说明 |
|------|------|------|
| `app/database/` | SQLAlchemy | ORM 模型、数据库连接 |
| `app/schemas/` | Pydantic | 请求/响应模型 |
| `data/` | 数据采集 | AkShare 客户端、服务 |

---

## 6. 验证安装

```python
# test_env.py
from dotenv import load_dotenv
import akshare as ak
import pandas as pd

load_dotenv()

# 测试 AkShare
print("AkShare version:", ak.__version__)

# 测试 pandas
print("Pandas version:", pd.__version__)

print("✅ 环境配置成功!")
```

运行:
```bash
python test_env.py
```

---

## 7. 常见问题

### Q: pip install 报错？

```bash
# 升级 pip
pip install --upgrade pip

# 使用国内镜像 (可选)
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q: psycopg2 安装失败？

```bash
# Ubuntu/Debian
sudo apt-get install libpq-dev

# macOS
brew install postgresql

# 然后重试
pip install psycopg2-binary
```

### Q: akshare 报错？

AkShare 依赖较多，首次安装可能需要几分钟。
如果失败，单独安装依赖:
```bash
pip install akshare --no-cache-dir
```
