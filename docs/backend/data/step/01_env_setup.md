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

fastapi==0.115.0
uvicorn[standard]==0.30.6
sqlalchemy==2.0.35
pydantic-settings==2.5.2

# 数据采集
akshare==1.18.64
pandas==2.2.3

# 数据库
psycopg2-binary==2.9.10
alembic==1.13.3

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

# 数据库 (PostgreSQL + pgvector)
DATABASE_URL=postgresql://postgres:zhouchenhui@223.109.49.63:5432/attribution
DATABASE_URL_ASYNC=postgresql+asyncpg://postgres:zhouchenhui@223.109.49.63:5432/attribution

# Redis
REDIS_URL=redis://223.109.49.63:6379/0

# API
API_V1_PREFIX=/api/v1
```

---

## 5. 目录结构

```
backend/
├── .env                  # 环境变量 (不要提交到 git)
├── .env.example          # 环境变量模板
├── requirements.txt     # Python 依赖
├── app/                  # API 应用
├── core/                 # 核心模块
├── data/                 # 数据采集
├── detector/             # 异常检测
├── scripts/              # 脚本
└── tests/               # 测试
```

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
