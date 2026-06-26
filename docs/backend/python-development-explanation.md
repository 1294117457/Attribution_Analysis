# Python 后端开发 — 详细说明

> 本文档：解释每一步的原理和原因
> 简明步骤：参考 `python-development-steps.md`

---

## 第一步：安装 Python 环境

### 做了什么

安装 Python 运行时和 pip（包管理工具）。

### 为什么这样做

Python 是整个后端项目的编程语言运行环境。没有 Python，后续所有代码都无法执行。

### 补充说明

- **Windows**：去 python.org 下载安装包，安装时记得勾选 "Add Python to PATH"
- **Linux**：大多数发行版预装了 Python，可用 `python3` 代替 `python`
- **pip** 是 Python 的包管理器，用来安装第三方库

---

## 第二步：pip 换源（国内加速）

### 做了什么

将 pip 默认的 PyPI 下载源（国外服务器）换成清华大学的镜像站。

### 为什么这样做

Python 的官方包仓库 PyPI 服务器在国外，国内直接访问速度很慢，经常超时。换源后下载速度提升显著。

### 补充说明

- 清华源：`https://pypi.tuna.tsinghua.edu.cn/simple`
- 其他国内源：阿里云、豆瓣等均可
- 配置一次后，所有后续 `pip install` 都自动使用这个源

---

## 第三步：创建虚拟环境

### 做了什么

在 `backend/` 目录下创建一个名为 `venv` 的虚拟环境，然后激活它。

### 为什么这样做

**虚拟环境**是一个独立的 Python 运行环境。每个项目的依赖包版本可能不同，放在同一个系统环境里会互相冲突。虚拟环境让每个项目有自己独立的依赖空间。

```
项目A 需要 requests==2.25
项目B 需要 requests==2.28
→ 放在同一个环境会打架
→ 用虚拟环境隔开，各自安好
```

### 补充说明

- `venv` 是 Python 3.3+ 内置的虚拟环境工具，无需额外安装
- 激活后，终端提示符前会显示 `(venv)` 标识
- Windows 用 `.\venv\Scripts\activate`，Linux/Mac 用 `source venv/bin/activate`
- `.gitignore` 里记得加上 `venv/`，不要提交到仓库

---

## 第四步：安装依赖包

### 做了什么

一次性安装所有需要的第三方库。

### 为什么这样做

每个库提供不同的能力：

| 库名 | 作用 |
|------|------|
| **fastapi** | Web 框架，用来构建 API 接口 |
| **uvicorn** | ASGI 服务器，用来运行 FastAPI 应用 |
| **sqlalchemy** | ORM 库，用来操作数据库（替代直接写 SQL） |
| **pydantic-settings** | 配置管理，从 .env 文件读取配置 |
| **akshare** | 财经数据接口，用来获取 A 股 K 线数据 |
| **pandas** | 数据处理库，用来处理表格数据 |

### 补充说明

- 激活虚拟环境后，`pip install` 会把包安装到当前虚拟环境，不会污染系统 Python
- 建议同时生成 `requirements.txt`：`pip freeze > requirements.txt`，方便在其他机器复现环境

---

## 第五步：配置环境变量

### 做了什么

在 `backend/.env` 文件中写入数据库连接字符串等配置。

### 为什么这样做

数据库密码、API 密钥等敏感信息不应该写死在代码里（会被提交到 Git）。`.env` 文件可以被 `.gitignore` 排除，起到隔离敏感信息的作用。

### .env 文件内容解释

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/attribution
```

- `postgresql://`：协议名
- `postgres:postgres`：用户名:密码
- `localhost:5432`：数据库地址:端口
- `attribution`：数据库名

### 补充说明

- `.env` 文件不要提交到 Git，在 `.gitignore` 中加一行 `.env`
- `pydantic-settings` 会自动读取 `.env` 文件并映射到 `Settings` 类

---

## 第六步：启动 PostgreSQL 数据库

### 做了什么

用 Docker 运行一个 PostgreSQL 容器。

### 为什么这样做

项目需要把股票数据持久化存储，PostgreSQL 是关系型数据库，适合存储结构化的 K 线数据。选择 Docker 的原因是：

1. **一键启动**：一行命令搞定，不需要手动安装配置
2. **环境隔离**：容器和宿主机系统隔离，不互相影响
3. **pgvector 扩展**：用了带向量的 pgvector 镜像，为后续 AI 能力做准备
4. **数据持久化**：指定端口映射 `5432:5432`，数据存在容器里

### 补充说明

- `--name attribution-postgres`：给容器起个名字，方便管理
- `-e POSTGRES_PASSWORD=postgres`：设置数据库密码
- `pgvector/pgvector:pg16`：带向量扩展的 PostgreSQL 16 镜像
- 如果没有 Docker，需要先安装 Docker Desktop

---

## 第七步：建表（用 SQL）

### 做了什么

用 SQL 语句在数据库中创建 `klines` 表。

### 为什么这样做

**两种方式都可以：**

| 方式 | 在哪写 | 适用场景 |
|------|--------|----------|
| **命令行 psql** | 服务器终端 | 一次性建表、快速调试 |
| **代码里执行 SQL** | Python 脚本 | 自动化、环境复现 |

两种方式本质一样——都是执行 SQL 语句建表。代码里执行的好处是：**换一台机器、换一个数据库，只要跑一下脚本，表就自动建好了。**

### SQL 建表语句解释

```sql
CREATE TABLE IF NOT EXISTS klines (
    id SERIAL PRIMARY KEY,           -- 自增主键
    code VARCHAR(10) NOT NULL,       -- 股票代码，如 600519
    name VARCHAR(50) NOT NULL,       -- 股票名称，如 贵州茅台
    date DATE NOT NULL,              -- 交易日期
    open FLOAT NOT NULL,             -- 开盘价
    high FLOAT NOT NULL,             -- 最高价
    low FLOAT NOT NULL,              -- 最低价
    close FLOAT NOT NULL,            -- 收盘价
    volume FLOAT NOT NULL,           -- 成交量
    amount FLOAT NOT NULL,           -- 成交额
    change_pct FLOAT,                -- 涨跌幅
    turnover_rate FLOAT              -- 换手率
);
```

### 索引的作用

```sql
CREATE UNIQUE INDEX idx_code_date ON klines(code, date);  -- 股票+日期唯一索引，防重复
CREATE INDEX idx_code ON klines(code);                     -- 按股票代码快速查询
CREATE INDEX idx_date ON klines(date);                     -- 按日期快速查询
```

**没有索引**：查 1 万条数据要扫描全表（慢）。
**有索引**：查 1 万条数据直接定位（快）。

### 补充说明

- `IF NOT EXISTS`：如果表已存在就跳过，不会报错
- 建表只需执行一次，之后不用再管
- 如果想删除重建：`DROP TABLE klines;` 然后重新执行建表

---

## 第八步：启动后端服务

### 做了什么

用 Uvicorn 运行 FastAPI 应用。

### 为什么这样做

FastAPI 本身是一个 ASGI 应用框架，需要一个 ASGI 服务器来托管。Uvicorn 就是这个服务器。

| 组件 | 作用 |
|------|------|
| **FastAPI** | 定义 API 路由、数据格式、业务逻辑 |
| **Uvicorn** | 运行 FastAPI 应用，处理 HTTP 请求 |

### 各参数含义

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- `app.main:app`：从 `app/main.py` 导入名为 `app` 的 FastAPI 实例
- `--reload`：代码改动后自动重启，开发时用（生产环境去掉）
- `--host 0.0.0.0`：监听所有网络接口，这样局域网其他设备也能访问
- `--port 8000`：监听 8000 端口

### 补充说明

- 启动后终端会显示 Uvicorn 的日志
- 按 `Ctrl+C` 停止服务

---

## 第九步：验证服务正常运行

### 做了什么

访问健康检查接口。

### 为什么这样做

`/health` 是一个最简单的接口，返回固定内容。如果它能正常返回，说明：

- FastAPI 应用加载成功
- Uvicorn 服务器运行正常
- 网络连接没问题

这是确认服务"活着"的最基本检查。

### 补充说明

- Swagger UI（http://localhost:8000/docs）是 FastAPI 自带的 API 文档页面，可以在这里测试所有接口
- ReDoc（http://localhost:8000/redoc）是另一种风格的文档页面

---

## 第十步：采集股票数据

### 做了什么

运行采集脚本，从 AkShare 获取 K 线数据并存入数据库。

### 为什么这样做

AkShare 是一个开源财经数据包，提供了获取 A 股、K 线、财务数据等的接口。采集脚本把 AkShare 返回的数据转换为数据库记录，然后批量写入 PostgreSQL。

### 代码流程解释

```
1. 调用 akshare → 获取 DataFrame（原始数据表格）
2. 遍历 DataFrame → 拼装 SQL INSERT 语句
3. 批量写入数据库 → execute() + commit()
```

### 补充说明

- `asyncio.sleep(1)` 是为了避免请求过快被封
- 股票代码 `600519` 是贵州茅台

---

## 第十一步：查询数据

### 做了什么

通过 HTTP 请求查询数据库中的 K 线数据。

### 为什么这样做

验证数据是否正确存储、API 是否正常工作。用 `curl` 或者浏览器直接访问即可，不需要写前端。

### URL 参数说明

```
?code=600519           # 股票代码
&start_date=2024-01-01  # 开始日期
&end_date=2024-06-25    # 结束日期
```

### 补充说明

- API 返回 JSON 格式，前端可以直接用
- 如果数据量很大，可以加 `limit` 和 `offset` 做分页

---

## 附录：各文件的作用

| 文件 | 作用 |
|------|------|
| `app/main.py` | FastAPI 入口，注册路由和中间件 |
| `app/config.py` | 配置管理，读取 .env |
| `app/db/database.py` | 数据库连接引擎 |
| `app/db/models.py` | ORM 模型（表结构的 Python 表示） |
| `app/api/v1/klines.py` | API 路由定义 |
| `scripts/init_db.py` | 建表脚本（执行一次） |
| `scripts/collect_data.py` | 数据采集脚本 |
| `.env` | 环境变量（敏感信息，不要提交） |

---

## 常见问题速查

| 问题 | 原因 | 解决 |
|------|------|------|
| AkShare 返回空 | 请求频率限制 | 加 `sleep(1)` 延迟 |
| PostgreSQL 连接失败 | 容器没启动 | `docker start attribution-postgres` |
| 中文乱码 | 数据库编码问题 | 确保用 UTF-8 |
| pip 安装超时 | 网络问题 | 换国内源（第二步） |
| 表已存在报错 | 没加 `IF NOT EXISTS` | 加上或在 psql 里加 `IF NOT EXISTS` |

---

## SQL 基础速查

| 操作 | SQL |
|------|-----|
| 建表 | `CREATE TABLE IF NOT EXISTS 表名 (...)` |
| 查数据 | `SELECT * FROM 表名 WHERE 条件` |
| 插入数据 | `INSERT INTO 表名 (列...) VALUES (值...)` |
| 删除数据 | `DELETE FROM 表名 WHERE 条件` |
| 删除表 | `DROP TABLE 表名` |
| 查看所有表 | `\dt`（在 psql 里） |
| 查看表结构 | `\d 表名`（在 psql 里） |
| 分页查询 | `SELECT * FROM 表名 LIMIT 10 OFFSET 0` |
| 按日期排序 | `ORDER BY date DESC` |
