# 部署配置

## 一、构建配置

### 1.1 pom.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.3.5</version>
        <relativePath/>
    </parent>

    <groupId>com.attribution</groupId>
    <artifactId>backend-java</artifactId>
    <version>3.0.0</version>
    <name>Attribution Analysis Backend (Java)</name>
    <description>Java 21 + Spring Boot 3 重构版</description>

    <properties>
        <java.version>21</java.version>
        <maven.compiler.source>21</maven.compiler.source>
        <maven.compiler.target>21</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>

        <!-- 依赖版本 -->
        <springdoc.version>2.6.0</springdoc.version>
        <lombok.version>1.18.34</lombok.version>
        <hibernate-jpa.version>3.1.0</hibernate-jpa.version>
    </properties>

    <dependencies>
        <!-- Spring Boot Starters -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-jpa</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-webflux</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-validation</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-actuator</artifactId>
        </dependency>

        <!-- Database -->
        <dependency>
            <groupId>org.postgresql</groupId>
            <artifactId>postgresql</artifactId>
            <scope>runtime</scope>
        </dependency>
        <dependency>
            <groupId>org.flywaydb</groupId>
            <artifactId>flyway-core</artifactId>
        </dependency>
        <dependency>
            <groupId>org.flywaydb</groupId>
            <artifactId>flyway-database-postgresql</artifactId>
        </dependency>

        <!-- JSONB 支持 -->
        <dependency>
            <groupId>io.hypersistence</groupId>
            <artifactId>hypersistence-utils-hibernate-63</artifactId>
            <version>3.8.3</version>
        </dependency>

        <!-- Lombok -->
        <dependency>
            <groupId>org.projectlombok</groupId>
            <artifactId>lombok</artifactId>
            <version>${lombok.version}</version>
            <scope>provided</scope>
        </dependency>

        <!-- API 文档 -->
        <dependency>
            <groupId>org.springdoc</groupId>
            <artifactId>springdoc-openapi-starter-webmvc-ui</artifactId>
            <version>${springdoc.version}</version>
        </dependency>

        <!-- 工具 -->
        <dependency>
            <groupId>org.apache.commons</groupId>
            <artifactId>commons-lang3</artifactId>
        </dependency>

        <!-- 测试 -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>org.testcontainers</groupId>
            <artifactId>postgresql</artifactId>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>org.testcontainers</groupId>
            <artifactId>junit-jupiter</artifactId>
            <scope>test</scope>
        </dependency>
    </dependencies>

    <build>
        <finalName>attribution-backend</finalName>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
                <configuration>
                    <excludes>
                        <exclude>
                            <groupId>org.projectlombok</groupId>
                            <artifactId>lombok</artifactId>
                        </exclude>
                    </excludes>
                </configuration>
            </plugin>

            <!-- JUnit 5 配置 -->
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-surefire-plugin</artifactId>
            </plugin>
        </plugins>
    </build>
</project>
```

### 1.2 settings.xml 镜像配置

```xml
<!-- ~/.m2/settings.xml -->
<settings>
    <mirrors>
        <mirror>
            <id>aliyun-public</id>
            <mirrorOf>*,!apache.snapshots</mirrorOf>
            <url>https://maven.aliyun.com/repository/public</url>
        </mirror>
    </mirrors>
</settings>
```

## 二、application.yml 完整配置

### 2.1 application.yml（默认）

```yaml
spring:
  application:
    name: attribution-analysis

  profiles:
    active: ${SPRING_PROFILES_ACTIVE:dev}

  datasource:
    url: ${DATABASE_URL:jdbc:postgresql://localhost:5432/attribution}
    username: ${DATABASE_USERNAME:postgres}
    password: ${DATABASE_PASSWORD:postgres}
    driver-class-name: org.postgresql.Driver
    hikari:
      maximum-pool-size: 200
      minimum-idle: 10
      connection-timeout: 30000
      idle-timeout: 600000
      max-lifetime: 1800000

  jpa:
    hibernate:
      ddl-auto: validate
    show-sql: false
    open-in-view: false
    properties:
      hibernate:
        dialect: org.hibernate.dialect.PostgreSQLDialect
        format_sql: true
        jdbc:
          time_zone: Asia/Shanghai
        order_inserts: true
        order_updates: true
        batch_size: 50

  flyway:
    enabled: true
    locations: classpath:db/migration
    baseline-on-migrate: true
    validate-on-migrate: true

  threads:
    virtual:
      enabled: true  # Spring Boot 3.3+ 启用虚拟线程

  jackson:
    date-format: yyyy-MM-dd HH:mm:ss
    time-zone: Asia/Shanghai
    serialization:
      write-dates-as-timestamps: false
      indent-output: false
    deserialization:
      fail-on-unknown-properties: false

server:
  port: ${SERVER_PORT:8000}
  compression:
    enabled: true
    mime-types: application/json,application/xml,text/html,text/plain
  tomcat:
    threads:
      max: 200
      min-spare: 10

logging:
  level:
    root: INFO
    com.attribution: DEBUG
    org.springframework.web: INFO
    org.hibernate.SQL: INFO
  pattern:
    console: "%d{yyyy-MM-dd HH:mm:ss.SSS} %-5level [%thread] %logger{36} - %msg%n"

tushare:
  token: ${TUSHARE_TOKEN:}
  base-url: http://api.tushare.pro
  timeout: 30000
  max-retries: 3
  rate-limit: 33  # 每秒请求数

collection:
  task:
    batch-size: 100
    batch-delay: 1000
    max-concurrency: 50
    default-lookback-days: 365

management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics,prometheus
  endpoint:
    health:
      show-details: when-authorized
```

### 2.2 application-dev.yml（开发环境）

```yaml
spring:
  datasource:
    url: jdbc:postgresql://localhost:5432/attribution_dev
    username: postgres
    password: postgres

logging:
  level:
    com.attribution: DEBUG
    org.hibernate.SQL: DEBUG
    org.hibernate.orm.jdbc.bind: TRACE

tushare:
  token: ${TUSHARE_TOKEN}
```

### 2.3 application-prod.yml（生产环境）

```yaml
spring:
  datasource:
    url: ${DATABASE_URL}
    username: ${DATABASE_USERNAME}
    password: ${DATABASE_PASSWORD}
    hikari:
      maximum-pool-size: 200
      minimum-idle: 20

logging:
  level:
    com.attribution: INFO

tushare:
  token: ${TUSHARE_TOKEN}
```

## 三、Docker 部署

### 3.1 Dockerfile（多阶段构建）

```dockerfile
# ── Stage 1: Build ──────────────────────────────────────────────
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /app

COPY pom.xml .
RUN mvn dependency:go-offline -B

COPY src ./src
RUN mvn package -DskipTests -B

# ── Stage 2: Runtime ────────────────────────────────────────────
FROM eclipse-temurin:21-jre-jammy
WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN mkdir -p /app/logs && chown -R appuser:appuser /app

COPY --from=build /app/target/attribution-backend.jar app.jar

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/actuator/health || exit 1

ENV JAVA_OPTS="-Xms512m -Xmx2g -XX:+UseG1GC -XX:MaxGCPauseMillis=200"

ENTRYPOINT ["sh", "-c", "exec java $JAVA_OPTS -jar app.jar"]
```

### 3.2 docker-compose.yml

```yaml
version: '3.8'

services:
  app:
    build: .
    image: attribution-backend:latest
    container_name: attribution-backend
    ports:
      - "8000:8000"
    environment:
      - SPRING_PROFILES_ACTIVE=prod
      - DATABASE_URL=jdbc:postgresql://postgres:5432/attribution
      - DATABASE_USERNAME=postgres
      - DATABASE_PASSWORD=${POSTGRES_PASSWORD:-postgres}
      - TUSHARE_TOKEN=${TUSHARE_TOKEN}
      - JAVA_OPTS=-Xms512m -Xmx2g
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - attribution-net

  postgres:
    image: postgres:15-alpine
    container_name: attribution-postgres
    environment:
      - POSTGRES_DB=attribution
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgres}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - attribution-net

volumes:
  postgres-data:
    driver: local

networks:
  attribution-net:
    driver: bridge
```

### 3.3 构建与启动

```bash
# 构建镜像
docker build -t attribution-backend:latest .

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f app

# 停止
docker-compose down

# 重新构建并启动
docker-compose up -d --build
```

## 四、Kubernetes 部署（生产级）

### 4.1 Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: attribution-backend
  namespace: attribution
spec:
  replicas: 3
  selector:
    matchLabels:
      app: attribution-backend
  template:
    metadata:
      labels:
        app: attribution-backend
    spec:
      containers:
        - name: app
          image: attribution-backend:latest
          ports:
            - containerPort: 8000
          env:
            - name: SPRING_PROFILES_ACTIVE
              value: prod
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: db-secret
                  key: url
            - name: DATABASE_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: db-secret
                  key: password
            - name: TUSHARE_TOKEN
              valueFrom:
                secretKeyRef:
                  name: tushare-secret
                  key: token
          resources:
            requests:
              memory: "512Mi"
              cpu: "500m"
            limits:
              memory: "2Gi"
              cpu: "2000m"
          livenessProbe:
            httpGet:
              path: /actuator/health/liveness
              port: 8000
            initialDelaySeconds: 60
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /actuator/health/readiness
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 5
```

### 4.2 Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: attribution-backend
  namespace: attribution
spec:
  selector:
    app: attribution-backend
  ports:
    - port: 80
      targetPort: 8000
  type: ClusterIP
```

### 4.3 Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: attribution-backend
  namespace: attribution
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
spec:
  ingressClassName: nginx
  rules:
    - host: api.attribution.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: attribution-backend
                port:
                  number: 80
```

## 五、Virtual Threads 调优

### 5.1 Spring Boot 3.3 配置

```yaml
spring:
  threads:
    virtual:
      enabled: true  # 自动为所有 @RestController 启用虚拟线程
```

### 5.2 JVM 参数

```bash
JAVA_OPTS="-Xms512m -Xmx2g \
  -XX:+UseG1GC \
  -XX:MaxGCPauseMillis=200 \
  -XX:+UseStringDeduplication \
  -Djdk.tracePinnedThreads=full"
```

### 5.3 性能监控

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics,prometheus
```

启用 `/actuator/metrics` 和 `/actuator/prometheus` 端点，结合 Prometheus + Grafana 监控。

## 六、数据库迁移

### 6.1 Flyway 迁移脚本结构

```
src/main/resources/db/migration/
├── V1__init_schema.sql          # 初始化表结构
├── V2__add_indicator_columns.sql # 添加技术指标列
└── V3__add_indexes.sql           # 添加索引
```

### 6.2 V1__init_schema.sql（示例）

由于 Python 项目已经存在数据库表，Flyway 迁移可以仅做 **兼容性确认**：

```sql
-- 验证表存在（不会重新创建）
-- 如果需要从空数据库初始化，可以参考 Python 项目的模型自动生成 SQL

-- 启用 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 创建必要索引（如果不存在）
CREATE INDEX IF NOT EXISTS ix_tech_kline_symbol_date ON tech_kline_dailys (symbol, date);
CREATE INDEX IF NOT EXISTS ix_pool_operations_status ON pool_operations (status);
```

## 七、运行验证

### 7.1 本地启动

```bash
# 编译
mvn clean package -DskipTests

# 运行
java -jar target/attribution-backend.jar

# 或者
mvn spring-boot:run
```

### 7.2 健康检查

```bash
curl http://localhost:8000/actuator/health

# 期望输出
{
  "status": "UP",
  "components": {
    "db": { "status": "UP" },
    "diskSpace": { "status": "UP" }
  }
}
```

### 7.3 API 测试

```bash
# 查询 K 线
curl http://localhost:8000/api/klines/000001.SZ

# 创建池
curl -X POST http://localhost:8000/api/pools \
  -H "Content-Type: application/json" \
  -d '{"name":"我的自选","poolType":"watchlist"}'

# 查看 API 文档
open http://localhost:8000/swagger-ui.html
```

## 八、与 Python 版本共存

### 8.1 端口隔离

| 服务 | 端口 |
|---|---|
| Python FastAPI | 8000 |
| Java Spring Boot | 8080 |
| PostgreSQL | 5432 |
| Prometheus | 9090 |

### 8.2 灰度切换

```
阶段 1: Python 8000 → 流量 100%
阶段 2: Python 8000 → 流量 80%, Java 8080 → 流量 20%
阶段 3: Python 8000 → 流量 50%, Java 8080 → 流量 50%
阶段 4: Python 8000 → 流量 20%, Java 8080 → 流量 80%
阶段 5: Java 8080 → 流量 100%, Python 8000 停机
```

Nginx 反向代理示例：

```nginx
upstream python_backend {
    server localhost:8000;
}

upstream java_backend {
    server localhost:8080;
}

server {
    listen 80;
    location / {
        # 灰度分流（基于权重）
        proxy_pass http://java_backend;
        # proxy_pass http://python_backend;
    }
}
```
