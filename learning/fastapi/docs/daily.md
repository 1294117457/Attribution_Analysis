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
create_engine,sessionmaker,declarative_base

# 1. 数据库配置（清晰可见）
SQLALCHEMY_DATABASE_URL = "sqlite:///./stocks.db"

# 2. 创建 engine（可以添加各种配置）
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

```

