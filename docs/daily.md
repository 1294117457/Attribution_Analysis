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
```

