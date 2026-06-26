# Python 后端开发 — 简明步骤

> 详细说明：参考 `python-development-explanation.md`

---

## 前提条件

- Python 3.10+
- Docker（用于运行 PostgreSQL）
- pip（包管理工具）

---

## 第一步：安装 Python 环境

```bash
python --version
pip --version
```

如果未安装，去 https://python.org 下载安装。

---

## 第二步：pip 换源（国内加速）

```bash
pip install pip -U
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 第三步：创建虚拟环境

```bash
cd backend
python -m venv venv
source venv/bin/activate    # Linux/Mac
# venv\Scripts\activate     # Windows
```

> **目的**：每个项目有独立的依赖空间，互不干扰。

---

## 第四步：安装依赖

```bash
pip install fastapi uvicorn sqlalchemy pydantic-settings akshare pandas
```

> **目的**：FastAPI 构建 API，SQLAlchemy 操作数据库，其他库处理数据。

---

## 第五步：配置环境变量

在 `backend/.env` 中写入：

```
DATABASE_URL=postgresql://postgres:你的密码@你的数据库地址:5432/attribution
```

---

## 第六步：启动 PostgreSQL 数据库

```bash
docker run -d \
  --name attribution-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=attribution \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```

> **目的**：PostgreSQL 是关系型数据库，用来存储股票数据。

---

## 第七步：建表（用 SQL）

**方式一：命令行一次性执行**

```bash
PGPASSWORD=你的密码 psql -h 你的数据库地址 -U postgres -d attribution -c '
CREATE TABLE IF NOT EXISTS klines (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) NOT NULL,
    name VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    open FLOAT NOT NULL,
    high FLOAT NOT NULL,
    low FLOAT NOT NULL,
    close FLOAT NOT NULL,
    volume FLOAT NOT NULL,
    amount FLOAT NOT NULL,
    change_pct FLOAT,
    turnover_rate FLOAT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_code_date ON klines(code, date);
CREATE INDEX IF NOT EXISTS idx_code ON klines(code);
CREATE INDEX IF NOT EXISTS idx_date ON klines(date);
'
```

**方式二：在代码里执行**

运行一次 `scripts/init_db.py`，自动建表：

```bash
python scripts/init_db.py
```

---

## 第八步：启动后端服务

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

服务运行在 http://localhost:8000
- Swagger UI：http://localhost:8000/docs
- ReDoc：http://localhost:8000/redoc

---

## 第九步：验证服务

```bash
curl http://localhost:8000/health
```

返回 `{"status":"ok"}` 即正常。

---

## 第十步：采集数据

```bash
cd backend
source venv/bin/activate
python scripts/collect_data.py
```

> **目的**：从 AkShare 获取 K 线数据，存入数据库。

---

## 第十一步：查询数据

```bash
curl "http://localhost:8000/api/v1/klines?code=600519&start_date=2024-01-01&end_date=2024-06-25"
```

---

## 常用命令汇总

| 操作 | 命令 |
|------|------|
| 启动服务 | `uvicorn app.main:app --reload` |
| 建表 | `python scripts/init_db.py` |
| 采集数据 | `python scripts/collect_data.py` |
| 查看数据库 | `psql -U postgres -d attribution` |
| 查看表数据 | `SELECT * FROM klines LIMIT 5;` |
| 删除表 | `DROP TABLE klines;` |
| 退出 psql | `\q` |
| 停 Docker | `docker stop attribution-postgres` |
| 删 Docker | `docker rm attribution-postgres` |

---

## 项目结构

```
backend/
├── app/
│   ├── main.py        # FastAPI 入口
│   ├── config.py      # 配置管理
│   ├── db/
│   │   ├── database.py  # 数据库连接
│   │   └── models.py    # ORM 模型
│   └── api/
│       └── v1/
│           └── klines.py  # API 路由
├── scripts/
│   ├── init_db.py     # 建表脚本
│   └── collect_data.py  # 采集脚本
├── .env               # 环境变量（不要提交）
└── requirements.txt   # 依赖列表
```

---

## 注意事项

- `.env` 文件包含数据库密码，**不要提交到 Git**
- 建表只需执行一次（`init_db.py`）
- 如果表已存在，`init_db.py` 会跳过已存在的表
