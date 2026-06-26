##### 1.总体架构

```
基于docker compose的微服务模式，
	后期可升级k8s编排
布局分为
	nginx网关、frontend，backend，agent，postgreSql，qdrant，redis
```

##### 2.backend

```
fastApi
	接收、持久化、处理数据
	涨跌幅计算、MA/EMA，3σ/IQR，同环比偏差、拐点检测
langgraph
	新闻情感分析，机器学习预测，经验积累
	LLM 生成自然语言报告
```

##### 3.**Persistence**

```
PostgreSql+pgvector

docker run -d --name attribution-postgres \
  -e POSTGRES_DB=attribution \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=zhouchenhui \
  -p 5432:5432 \
  -v /home/project/postgre/data:/var/lib/postgresql/data \
  --restart unless-stopped \
  pgvector/pgvector:pg16 \
  -c 'listen_addresses=*' \
  -c 'max_connections=100'
  
  容器 (attribution-postgres)
│
├── PostgreSQL 16 + pgvector 扩展
│   ├── 数据目录: /var/lib/postgresql/data (挂载到宿主机)
│   ├── 配置文件: /var/lib/postgresql/data/postgresql.conf
│   ├── 认证配置: /var/lib/postgresql/data/pg_hba.conf
│   └── 数据库文件: /var/lib/postgresql/data/base/
│
├── 数据库 (attribution)  ← 你创建的数据库
│   ├── 默认 Schema: public
│   ├── 系统表: pg_catalog, information_schema
│   └── (你后续会创建的表: stock_klines, ...)
│
├── 系统数据库 (自动创建)
│   ├── postgres      ← 默认管理数据库
│   ├── template0     ← 模板库（只读）
│   └── template1     ← 模板库（可修改）
│
└── 用户 (postgres)   ← 超级用户
```

```
整体还是一个postgre数据库，只是带了pgvector扩展
然后内部数据表可以带embedding字段
```

