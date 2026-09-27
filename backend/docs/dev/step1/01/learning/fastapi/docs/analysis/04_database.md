# 数据库连接详解

## 一、ORM 概念

### 什么是 ORM？

```
ORM (Object-Relational Mapping)
对象关系映射

SQL 表                    Python 对象
┌─────────────────┐      ┌─────────────────┐
│ stocks          │      │ class Stock     │
├─────────────────┤      ├─────────────────┤
│ code (PK)       │ ←──→ │ stock.code      │
│ name            │ ←──→ │ stock.name      │
│ price           │ ←──→ │ stock.price     │
│ change          │ ←──→ │ stock.change    │
└─────────────────┘      └─────────────────┘
```

### 不用 ORM vs 用 ORM

```python
# ❌ 不用 ORM：写原生 SQL
cursor.execute("SELECT * FROM stocks WHERE code = ?", (code,))
result = cursor.fetchone()
price = result[2]

# ✅ 用 ORM：操作 Python 对象
stock = db.query(Stock).filter(Stock.code == code).first()
price = stock.price
```

## 二、SQLAlchemy 核心概念

```
SQLAlchemy 结构
├── create_engine()      # 创建数据库连接引擎
├── sessionmaker()       # 创建会话工厂
├── declarative_base()    # 创建模型基类
├── Base                 # 继承的基类
│   └── 定义模型类         # 映射到表
└── Session              # 执行 CRUD 操作
```

## 三、数据库连接配置

### SQLite（开发/测试）

```python
from sqlalchemy import create_engine

# SQLite 相对路径
engine = create_engine("sqlite:///stocks.db")

# SQLite 绝对路径
engine = create_engine("sqlite:////absolute/path/to/stocks.db")

# SQLite 内存数据库（临时）
engine = create_engine("sqlite:///:memory:")

# SQLite 多线程支持
engine = create_engine(
    "sqlite:///stocks.db",
    connect_args={"check_same_thread": False}
)
```

### PostgreSQL

```python
# 使用 psycopg2
engine = create_engine(
    "postgresql://user:password@localhost:5432/stocks"
)

# 使用环境变量
import os
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@localhost:5432/stocks"
)
engine = create_engine(DATABASE_URL)
```

### MySQL

```python
# 使用 pymysql
engine = create_engine(
    "mysql+pymysql://user:password@localhost:3306/stocks"
)
```

## 四、定义数据模型

### 基本结构

```python
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class Stock(Base):
    __tablename__ = "stocks"  # 数据库表名
    
    # 主键
    code = Column(String(6), primary_key=True, index=True)
    
    # 普通字段
    name = Column(String(100), nullable=False)  # nullable=False = 必填
    price = Column(Float, default=0.0)
    volume = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
```

### 常用字段类型

| SQLAlchemy | Python | 说明 |
|------------|--------|------|
| `String(n)` | `str` | 字符串，最大 n 字符 |
| `Integer` | `int` | 整数 |
| `Float` | `float` | 浮点数 |
| `Boolean` | `bool` | 布尔值 |
| `DateTime` | `datetime` | 日期时间 |
| `Text` | `str` | 长文本 |
| `JSON` | `dict` | JSON 数据 |

### 常用字段参数

```python
from sqlalchemy import Column, String, Integer

class Example(Base):
    # 主键
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # 普通字段
    name = Column(String(100), nullable=False)  # 必填
    desc = Column(String(500), nullable=True)  # 可选
    default_val = Column(String(50), default="默认")  # 默认值
    
    # 索引
    email = Column(String(100), unique=True, index=True)  # 唯一索引
    category = Column(String(50), index=True)  # 普通索引
    
    # 外键
    user_id = Column(Integer, ForeignKey("users.id"))
```

## 五、会话管理

### 创建会话

```python
from sqlalchemy.orm import sessionmaker

SessionLocal = sessionmaker(
    autocommit=False,  # 默认不自动提交
    autoflush=False,   # 默认不自动刷新
    bind=engine        # 绑定引擎
)

# 创建会话
db = SessionLocal()
try:
    # 使用会话
    ...
finally:
    db.close()  # 务必关闭
```

### 依赖注入方式

```python
from typing import Generator
from fastapi import Depends

def get_db() -> Generator[Session, None, None]:
    """数据库会话依赖"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 使用
@app.get("/stocks")
def list_stocks(db: Session = Depends(get_db)):
    stocks = db.query(Stock).all()
    return stocks
```

## 六、CRUD 操作

### 1. 创建 (Create)

```python
# 创建单条
stock = Stock(code="600519", name="贵州茅台", price=1500)
db.add(stock)
db.commit()
db.refresh(stock)  # 获取数据库生成的值

# 批量创建
stocks = [
    Stock(code="600519", name="贵州茅台", price=1500),
    Stock(code="000858", name="五粮液", price=150),
]
db.add_all(stocks)
db.commit()
```

### 2. 读取 (Read)

```python
# 查询所有
stocks = db.query(Stock).all()

# 条件查询
stock = db.query(Stock).filter(Stock.code == "600519").first()

# 多个条件
stocks = db.query(Stock).filter(
    Stock.price > 100,
    Stock.volume > 1000000
).all()

# 模糊查询
stocks = db.query(Stock).filter(Stock.name.like("%茅台%")).all()

# 排序
stocks = db.query(Stock).order_by(Stock.price.desc()).all()

# 分页
stocks = db.query(Stock).offset(0).limit(10).all()

# 计数
count = db.query(Stock).filter(Stock.price > 100).count()
```

### 3. 更新 (Update)

```python
# 方式1：先查后改
stock = db.query(Stock).filter(Stock.code == "600519").first()
stock.price = 1600
db.commit()

# 方式2：批量更新
db.query(Stock).filter(Stock.price > 100).update({Stock.price: 0})
db.commit()

# 方式3：更新多个字段
db.query(Stock).filter(Stock.code == "600519").update({
    Stock.price: 1600,
    Stock.change: 3.5,
    Stock.updated_at: datetime.now()
})
db.commit()
```

### 4. 删除 (Delete)

```python
# 先查后删
stock = db.query(Stock).filter(Stock.code == "600519").first()
if stock:
    db.delete(stock)
    db.commit()

# 批量删除
db.query(Stock).filter(Stock.price < 1).delete()
db.commit()
```

## 七、关系映射

### 一对多

```python
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    
    # 关系：一对多
    posts = relationship("Post", back_populates="author")

class Post(Base):
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200))
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # 反向关系
    author = relationship("User", back_populates="posts")
```

### 使用关系

```python
# 查询用户及其所有文章
user = db.query(User).filter(User.id == 1).first()
for post in user.posts:  # 自动加载关联数据
    print(post.title)

# 关系是懒加载的，性能考虑可用 eager loading
from sqlalchemy.orm import joinedload

user = db.query(User).options(joinedload(User.posts)).first()
```

## 八、数据库迁移

### 使用 Alembic（推荐）

```bash
# 安装
pip install alembic

# 初始化
alembic init alembic

# 配置 alembic.ini 中的 sqlalchemy.url

# 创建迁移脚本
alembic revision --autogenerate -m "add stocks table"

# 执行迁移
alembic upgrade head
```

### 手动迁移（简单项目）

```python
# 创建表
Base.metadata.create_all(bind=engine)

# 删除表
Base.metadata.drop_all(bind=engine)
```

## 九、常见问题

### 1. Session 生命周期

```python
# ❌ 错误：会话泄漏
@app.get("/stocks")
def list_stocks(db: Session = Depends(get_db)):
    stocks = db.query(Stock).all()
    # 没关闭会话
    return stocks

# ✅ 正确：使用 yield
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 2. 事务管理

```python
# ❌ 错误：自动提交导致数据不一致
db.add(stock1)
db.add(stock2)
# 如果 stock2 失败，stock1 已经提交了

# ✅ 正确：显式事务
try:
    db.add(stock1)
    db.add(stock2)
    db.commit()  # 一起提交
except:
    db.rollback()  # 一起回滚
    raise
```

### 3. N+1 查询问题

```python
# ❌ N+1 查询
users = db.query(User).all()
for user in users:
    print(user.posts)  # 每访问一次就查一次

# ✅ 预加载
users = db.query(User).options(joinedload(User.posts)).all()
for user in users:
    print(user.posts)  # 一次查询全部加载
```

## 练习题

1. 创建一个「用户」表，包含 id、username、email、created_at
2. 实现用户的增删改查 API
3. 为股票表添加「行业」字段，实现按行业查询
4. 创建「文章」和「评论」表，实现一对多关系查询
5. 实现带分页和排序的股票列表 API
