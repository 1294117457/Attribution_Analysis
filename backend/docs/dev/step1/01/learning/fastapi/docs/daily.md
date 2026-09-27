##### 1fastAPi

```
unicorn  01demo:app --host 0.0.0.0 --port 8000 --reload

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
```

##### 2pydantic

```
BaseModel,@validator,Optional,Field

BaseModel
	定义字段类型，校验字段类型，转换字段类型
	json序列化，ConfigDict
	ConfigDict
		model_config = ConfigDict(
            str_strip_whitespace=True,  # ✅ 开关打开：自动去空格
            # from_attributes=True,     # ❌ 开关关闭：不支持ORM对象
            # populate_by_name=True     # ❌ 开关关闭：不支持别名
        )
```

##### 3sqlalchemy

```
服务器配置好数据库
代码中实现数据库、表操作等
```



```
create_engine,sessionmaker,declarative_base

SQLALCHEMY_DATABASE_URL = "sqlite:///./stocks.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite 专用
    echo=True,                                   # 打印 SQL 日志（开发环境）
    pool_size=5,                                 # 连接池大小
    max_overflow=10                              # 最大溢出连接数
)

# 3. 创建 SessionLocal（可复用）
SessionLocal = sessionmaker(
    autocommit=False,    # 不自动提交
    autoflush=False,     # 不自动刷新
    bind=engine
)

# 4. 创建 Base（所有模型的基类）
Base = declarative_base()

# 5. 获取 session 的函数（依赖注入用）
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def init_db():
    """启动时初始化数据库"""
    db = SessionLocal()
    try:
```

##### 4middleware

```

```

##### 5architeture

```
Stock是全局模型，
StockDB是数据库操作需要的映射模型并且实现对应方法
StockApi,StockService实现接收、处理数据，并且从StockDB获取Stock的数据库操作

pydantic的模型和StockDB分别放在
	app/models
	app/database/models
	
app/
├── models/                      # Pydantic 模型（全局数据模型）
│   ├── __init__.py
│   ├── stock.py                 # Stock (Pydantic)
│   ├── user.py                  # User (Pydantic)
│   └── order.py                 # Order (Pydantic)
│
├── database/                    # 或 db/
│   ├── __init__.py
│   ├── base.py                  # SQLAlchemy Base
│   ├── session.py               # 数据库连接
│   └── models/                  # SQLAlchemy 模型（数据库映射）
│       ├── __init__.py
│       ├── stock.py             # StockDB
│       ├── user.py              # UserDB
│       └── order.py             # OrderDB
│
├── services/                    # 业务逻辑层
│   ├── __init__.py
│   ├── stock_service.py
│   └── user_service.py
│
├── api/                         # 路由层
│   └── v1/
│       ├── __init__.py
│       ├── stock.py             # StockApi
│       └── user.py
│
└── main.py                      # FastAPI 入口
```

