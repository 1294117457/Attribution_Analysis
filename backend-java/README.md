# Attribution Analysis Backend (Java)

Java 21 + Spring Boot 3.3 重构版智能金融数据归因分析平台。

## 技术栈

- JDK 21 (Virtual Threads)
- Spring Boot 3.3.5
- Spring Data JPA + Hibernate 6
- PostgreSQL 15+
- Flyway 10
- SpringDoc OpenAPI 2.6

## 快速开始

### 前置条件

- JDK 21
- Maven 3.9+
- PostgreSQL 15+

### 配置

编辑 `src/main/resources/application-dev.yml`，设置：

```yaml
spring:
  datasource:
    url: jdbc:postgresql://localhost:5432/attribution
    username: postgres
    password: postgres

tushare:
  token: your-tushare-token
```

### 构建

```bash
mvn clean package -DskipTests
```

### 运行

```bash
mvn spring-boot:run
```

或：

```bash
java -jar target/attribution-backend.jar
```

访问：
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/swagger-ui.html
- 健康检查: http://localhost:8000/actuator/health

## 项目结构

```
src/main/java/com/attribution/
├── AttributionApplication.java      # 启动类
├── controller/                      # REST API 控制器
├── service/                         # 应用服务
├── domain/
│   ├── entity/                      # 聚合根与实体
│   ├── vo/                          # 值对象
│   └── event/                       # 领域事件
├── repository/                      # JPA Repository
├── adapter/collector/               # 数据采集器
├── config/                          # 配置类
├── dto/                             # Request/Response DTO
└── exception/                       # 异常处理

src/main/resources/
├── application.yml
├── application-dev.yml
└── db/migration/                    # Flyway 迁移脚本
```

## 数据采集器

| 数据源 | 实现 | 协议 | 备注 |
|--------|------|------|------|
| Tushare | `TushareApiClient` | HTTP REST (api.tushare.pro) | 主路径，所有 23 张表 |
| AKShare | `AkShareConceptCollector` | HTTP REST (push2.eastmoney.com) | 概念清单与成分股，Java 原生实现，无需 Python |
| Pytdx | `PytdxMinuteKlineCollector` | HTTP REST (stk_mins / 新浪) | 分钟 K 线，主路径 Tushare `stk_mins`，fallback 新浪 |

## 重构文档

详见 `docs/rebuild/` 目录：

- `00-overview.md` - 项目目标与范围
- `01-tech-stack.md` - 技术选型
- `02-architecture.md` - 分层架构
- `03-domain-mapping.md` - Python→Java 映射规则
- `04-data-collection.md` - 数据采集设计
- `05-api-migration.md` - API 迁移对照
- `06-deployment.md` - 部署配置
- `07-roadmap.md` - 6 周迁移计划
