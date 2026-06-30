# 项目进度文档 - 2026-06-30

## 一、项目概述

**智能金融数据归因分析平台** - 一个用于采集股票K线数据、进行异常检测和归因分析的金融数据分析系统。

## 二、技术栈

| 模块 | 技术 |
|------|------|
| 后端 | Python 3.12 + FastAPI + SQLAlchemy |
| 前端 | Vue 3 + Vite + Axios + Vue Router |
| 数据库 | SQLite (开发) / PostgreSQL (生产) |
| 数据源 | AkShare (东方财富) |

## 三、项目结构

```
Attribution_Analysis/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── api/
│   │   │   ├── router.py       # 路由汇总
│   │   │   └── v1/
│   │   │       ├── health.py   # 健康检查
│   │   │       └── stocks.py   # 股票数据 API
│   │   ├── schemas/
│   │   │   └── stock.py        # Pydantic 模型
│   │   ├── dependencies.py     # 依赖注入
│   │   └── main.py             # 应用入口
│   ├── data/
│   │   ├── adapters/akshare/   # AkShare 适配器
│   │   ├── collectors/          # 采集器
│   │   ├── interfaces/         # 采集参数协议
│   │   ├── parsers/            # 数据解析器
│   │   ├── schemas/            # 数据结构
│   │   └── services/           # 业务服务
│   │       └── stock_service.py
│   ├── infra/
│   │   ├── config.py           # 配置管理
│   │   └── database/
│   │       ├── base.py         # SQLAlchemy Base
│   │       ├── connection.py    # 数据库连接
│   │       └── models/         # ORM 模型
│   │           ├── stock.py       # DailyKlineDB
│   │           ├── stock_info.py  # StockInfoDB
│   │           └── mixins.py
│   ├── requirements.txt
│   └── .env                    # 环境配置
│
├── frontend/                   # Vue3 前端
│   ├── src/
│   │   ├── main.js             # 入口
│   │   ├── App.vue             # 根组件
│   │   ├── router/
│   │   │   └── index.js        # 路由配置
│   │   ├── api/
│   │   │   └── stock.js        # API 服务层
│   │   └── views/
│   │       ├── CollectPage.vue  # 数据采集页
│   │       └── ManagePage.vue  # 数据管理页
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
│
└── docs/
    └── backend/data/
        └── api_design.md       # API 设计文档
```

## 四、数据库模型

### 4.1 StockInfoDB (股票信息表)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| symbol | String(10) | 股票代码 (唯一) |
| name | String(50) | 股票名称 |
| industry | String(100) | 所属行业 |
| market | String(50) | 市场 |
| list_date | String(20) | 上市日期 |
| total_shares | String(50) | 总股本 |

### 4.2 DailyKlineDB (日K线表)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| symbol | String(10) | 股票代码 |
| name | String(50) | 股票名称 |
| date | Date | 交易日期 |
| open | Float | 开盘价 |
| high | Float | 最高价 |
| low | Float | 最低价 |
| close | Float | 收盘价 |
| volume | Integer | 成交量 |
| amount | Float | 成交额 |
| change_pct | Float | 涨跌幅 |

**唯一索引**: `(symbol, date)`

## 五、API 接口

### 5.1 股票管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/stocks/` | 获取股票列表 |
| GET | `/api/v1/stocks/{symbol}` | 获取股票详情 |
| POST | `/api/v1/stocks/collect` | 采集股票数据 |
| DELETE | `/api/v1/stocks/{symbol}` | 删除股票及K线 |

### 5.2 K线数据

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/stocks/{symbol}/klines` | 获取K线数据 |
| DELETE | `/api/v1/stocks/{symbol}/klines/{date}` | 删除单条K线 |

### 5.3 健康检查

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 服务健康检查 |

### 5.4 请求/响应示例

**采集请求**:
```json
POST /api/v1/stocks/collect
{
  "symbol": "000001",
  "days": 365
}
```

**采集响应**:
```json
{
  "status": "success",
  "symbol": "000001",
  "name": "平安银行",
  "count": 4,
  "message": "成功采集并存储 4 条数据"
}
```

**股票列表响应**:
```json
{
  "total": 1,
  "items": [
    {
      "symbol": "000001",
      "name": "平安银行",
      "industry": null,
      "market": null,
      "record_count": 4,
      "kline_start": "2026-06-25",
      "kline_end": "2026-06-30"
    }
  ]
}
```

## 六、前端页面

### 6.1 数据采集页 (`/`)

- 输入股票代码
- 设置采集天数
- 点击采集
- 展示采集结果和数据预览

### 6.2 数据管理页 (`/manage`)

- 显示所有已采集股票列表
- 显示统计数据（股票数量、数据总量）
- 查看单只股票的K线详情
- 删除股票或单条K线

## 七、数据流

```
用户输入股票代码
       ↓
前端 POST /api/v1/stocks/collect
       ↓
后端 StockService.collect_and_save()
       ↓
Collector → AkShareFetcher → AkShare API
       ↓
解析数据并存储到 SQLite
       ↓
返回结果给前端
       ↓
前端展示采集结果
```

## 八、已实现功能

| 功能 | 状态 | 说明 |
|------|------|------|
| 数据采集 | ✅ | 从 AkShare 获取日K线数据 |
| 数据存储 | ✅ | 去重插入，支持 SQLite/PostgreSQL |
| 股票信息管理 | ✅ | StockInfoDB 模型 |
| 股票列表 | ✅ | 含统计信息（条数、日期范围） |
| 删除股票 | ✅ | 删除所有K线数据 |
| 删除单条 | ✅ | 删除指定日期K线 |
| 前端 Vue3 | ✅ | 采集页 + 管理页 |
| CORS | ✅ | 允许跨域访问 |

## 九、待实现功能

| 功能 | 优先级 | 说明 |
|------|--------|------|
| 异常检测 | 高 | 基于统计的异常K线检测 |
| 归因分析 | 高 | 分析异常原因 |
| 批量采集 | 中 | 批量导入股票代码 |
| 数据导出 | 中 | 导出 CSV/Excel |
| 用户认证 | 低 | 登录注册功能 |

## 十、启动方式

### 10.1 后端

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

### 10.2 前端

```bash
cd frontend
npm install
npm run dev
```

### 10.3 访问

- 后端 API: http://localhost:8000
- 前端页面: http://localhost:3000
- API 文档: http://localhost:8000/docs

## 十一、配置说明

### 11.1 数据库配置 (.env)

```bash
# SQLite (开发)
DATABASE_URL=sqlite:///attribution.db

# PostgreSQL (生产)
DATABASE_URL=postgresql://user:pass@host:5432/attribution
```

### 11.2 数据源配置

当前使用 AkShare (东方财富)，无需额外配置 API Key。

## 十二、测试验证

已通过以下测试：

1. **采集功能**: 成功采集 `000001` 平安银行 4 条K线数据
2. **去重采集**: 重复采集返回 0 条新增
3. **股票列表**: 正确显示股票信息和统计
4. **删除单条**: 成功删除指定日期K线
5. **删除股票**: 成功删除股票所有数据

## 十三、注意事项

1. AkShare 依赖网络访问，确保服务器能访问东方财富 API
2. 采集频率不要过高，避免被限流
3. 生产环境建议使用 PostgreSQL
4. 前端代理已配置 `/api` → `localhost:8000`
