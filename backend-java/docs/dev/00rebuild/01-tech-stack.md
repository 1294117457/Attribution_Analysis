# 技术选型

## 一、核心技术栈

| 层级 | 技术 | 版本 | 说明 |
|---|---|---|---|
| 语言 | Java | 21 LTS | Virtual Threads (Project Loom) |
| 框架 | Spring Boot | 3.3.x | Jakarta EE 10, GraalVM Native 支持 |
| ORM | Spring Data JPA + Hibernate | 6.x | JPA 3.1，与 Hibernate 6 集成 |
| 异步 HTTP | Spring WebClient | 6.x | 替代 RestTemplate，响应式非阻塞 |
| 数据库 | PostgreSQL | 15+ | 已有 pgvector 扩展，复用现有实例 |
| 数据库迁移 | Flyway | 10.x | SQL-first 迁移，与 SQLAlchemy Alembic 对应 |
| 构建 | Maven | 3.9+ | 已配置阿里云镜像 |
| 部署 | Docker | 24+ | Multi-stage build |
| API 文档 | SpringDoc OpenAPI | 2.x | 替代 FastAPI auto-generated docs |
| 测试 | JUnit 5 + Mockito | latest | 单元测试 + 集成测试 |

## 二、选型理由详解

### 2.1 为什么是 Java 21

#### Virtual Threads（Project Loom）
Python FastAPI 使用 `async/await` 处理并发，每个请求一个协程。当有 10,000 个并发采集任务时，Python 需要 10,000 个协程。

Java 21 Virtual Threads：
- **轻量级**：每个 Virtual Thread 仅占用 ~1KB（vs ~1MB 平台线程）
- **无感切换**：不需要手动标记 `suspend/resume`，代码看起来像同步
- **无需 asyncio**：消除 `async/await` 地狱
- **与现有库兼容**：99% 的 Java 库无需修改即可在 Virtual Threads 中运行

```
Python (FastAPI):          Java 21 (Virtual Threads):
─────────────────          ─────────────────────────
async def handler():       @GetMapping("/api")
    await fetch()              String result = restTemplate.get(...);
    return resp                    // 看起来是同步，但底层是虚拟线程
```

#### 金融场景收益
当前 Python 项目需要同时：
- 维护 Tushare API 连接池
- 处理 Pytdx TCP 长连接
- 管理 asyncio 任务队列

Java Virtual Threads 让这些变成普通的线程操作，代码复杂度大幅降低。

#### Java 21 LTS 支持周期
- Oracle Premier Support: 2031 年 9 月
- 相比 Java 17（LTS）有更长的支持周期

### 2.2 为什么是 Spring Boot 3.3

#### 与 Python FastAPI 的对应关系

| Python FastAPI | Spring Boot 3.3 | 说明 |
|---|---|---|
| `@app.post()` | `@PostMapping` | REST 端点 |
| `async def` | `virtual thread` | 异步处理 |
| `Pydantic BaseModel` | `@Data` + `@Schema` | 数据校验 |
| `Depends()` | `@Autowired` + Constructor DI | 依赖注入 |
| `lifespan` | `@PostConstruct` / `@PreDestroy` | 生命周期 |
| `RequestValidationError` | `MethodArgumentNotValidException` | 参数校验 |
| `HTTPException` | `@ResponseStatus` / `ResponseEntity` | HTTP 错误 |
| `routing` | `@RequestMapping` | 路由注册 |

#### Spring Boot 3.3 特有优化
- **AOT Native Image**：启动时间从 2-3s 降至 <100ms
- **Observability**：Micrometer 指标开箱即用
- **Virtual Threads 自动检测**：自动为 `@RestController` 启用虚拟线程

### 2.3 为什么是 Spring Data JPA + Hibernate

#### 与 SQLAlchemy 2.0 的对应关系

| Python SQLAlchemy | Java JPA | 说明 |
|---|---|---|
| `Base` | `@Entity` | 模型基类 |
| `Mapped` | `@Column` | 列映射 |
| `relationship()` | `@OneToMany` / `@ManyToOne` | 关联关系 |
| `async_session` | `EntityManager` (async) | 会话管理 |
| `AsyncSession.execute()` | `EntityManager.createQuery()` | 查询执行 |
| `select(Model).where()` | `jpql` / Criteria API | 查询构建 |
| `unique_constraint` | `@Table(uniqueConstraints)` | 唯一约束 |
| `Index` | `@Table(indexes)` | 索引定义 |

#### 迁移优势
1. **现有 SQLAlchemy 模型可直接翻译**：字段类型、约束、索引一一对应
2. **无需学习新查询语言**：JPQL 与 SQL 相近
3. **Hibernate 6.4+**：支持 `Instant`、`Duration` 等 Java 8+ 时间类型原生映射
4. **Jakarta Persistence**：从 `javax.persistence` 迁移完成，API 稳定

### 2.4 为什么用 Flyway 而非 JPA Schema Generation

| 对比项 | Flyway | JPA `ddl-auto` |
|---|---|---|
| 版本控制 | SQL 文件，纳入 Git | 自动生成，不可控 |
| 生产安全 | ✅ 幂等迁移，可回滚 | ❌ 生产环境禁用 |
| 多数据库 | ✅ 仅 PostgreSQL 迁移 | 跨数据库麻烦 |
| 与现有 DB 兼容 | ✅ 可写 `IF NOT EXISTS` | ❌ 每次重建 |
| 学习曲线 | 低（纯 SQL） | 中（注解配置） |

**策略**：复用 Python 项目的数据库表结构，仅写 Flyway 迁移用于初始化。

### 2.5 为什么用 Spring WebClient

#### 与 Python httpx / requests 的对应关系

```python
# Python
response = requests.get(url, params=params, headers=headers)
data = response.json()
```

```java
// Java Spring WebClient
Mono<JsonNode> data = webClient.get()
    .uri(uriBuilder -> uriBuilder.path(url).queryParam("api_code", token).build())
    .header("Content-Type", "application/json")
    .retrieve()
    .bodyToMono(JsonNode.class);
```

#### 优势
- **非阻塞**：与 Virtual Threads 完美配合
- **背压控制**：内置，避免请求堆积
- **链式 API**：比 `RestTemplate` 更易读

## 三、技术约束与决策

### 3.1 禁止使用

| 技术 | 禁止原因 |
|---|---|
| `spring-boot-starter-web` (Tomcat) | 内置线程池，与 Virtual Threads 冲突 |
| `synchronized` 关键字 | Virtual Threads 中行为不同 |
| `ThreadLocal` | 改用 `ThreadLocal.withInitial()` + 清理 |
| `Object.wait()` / `Thread.sleep()` | Virtual Threads 中用 `LockSupport.parkNanos()` |

### 3.2 必须配置

```yaml
# application.yml
spring:
  threads:
    virtual:
      enabled: true  # Spring Boot 3.3+ 自动检测，可不写
  datasource:
    hikari:
      maximum-pool-size: 200  # Virtual Threads 建议调高
      minimum-idle: 10
```

### 3.3 建议启用

```xml
<!-- pom.xml -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-webflux</artifactId>
    <!-- WebClient 内嵌，不需要单独引入 netty -->
</dependency>
```

## 四、环境要求

| 组件 | 最低版本 | 推荐版本 |
|---|---|---|
| JDK | 21 | 21.0.12+ |
| Maven | 3.9 | 3.9.9+ |
| PostgreSQL | 15 | 16 |
| Docker | 24 | 25 |
| 操作系统 | Windows 10+ / Linux | Windows 11 / Ubuntu 22.04 |

## 五、替代方案评估

| 方案 | 放弃原因 |
|---|---|
| Kotlin + Coroutines | 团队 Java 背景，Kotlin 学习成本 |
| Quarkus | 生态不如 Spring Boot 成熟 |
| Micronaut | 相似，但 Spring Boot 文档更丰富 |
| GraalVM Native Image | 启动优化，但编译时间长，调试不便 |
| Spring Web Flux (Reactive) | 太陡的学习曲线，Virtual Threads 更自然 |
