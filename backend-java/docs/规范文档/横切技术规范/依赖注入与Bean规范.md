# 依赖注入与 Bean 规范

> 适用范围：`backend-java` 全部 Maven 模块
> 核心原则：**依赖是必需的、不可变的、在构造时就绪的——所以只允许构造器注入。**
> 配套文档：`../纵向分层规范/Service层规范.md`（谁该注入什么）、`../纵向分层规范/Controller层规范.md`（Controller 的注入约定）、`异常与响应规范.md`（Bean 创建失败怎么表达）、`基础设施规范.md`（线程池 / 连接池等资源型 Bean）

---

## 0. 一句话结论

> **全项目只允许构造器注入，禁止 `@Autowired` / `@Resource` 字段注入。**
> **依赖声明为 `private final`，默认用 Lombok `@RequiredArgsConstructor`，需要 `@Qualifier` 时手写构造器。**
> **共享资源（线程池 / 连接池 / HTTP 客户端）必须由 Spring 创建，禁止在业务代码里 `new`。**

---

## 1. 职责速查

| Bean 类型 | 谁创建 | 归属 | 例子 |
|---|---|---|---|
| **业务 Bean**（Controller / Service）| Spring 容器 | 各模块 | `PoolServiceImpl`、`AuthServiceImpl` |
| **Mapper** | MyBatis-Plus 代理 | 各模块 `mapper/` | `PoolMemberMapper` |
| **基础设施 Bean**（连接池 / 线程池 / 客户端）| `@Bean` 方法 | 各模块 `config/` | `poolTaskExecutor` |
| **框架 Bean**（Redis / Jackson / 数据源）| Spring Boot 自动配置 | 框架 | `StringRedisTemplate`、`ObjectMapper` |

**判断标准**：

| 问自己 | 是 → | 否 → |
|---|---|---|
| 这个 Bean 有生命周期（要关闭 / 要调 `initialize()`）吗？| 由 Spring 管理（`@Bean`）| 由业务代码 `new` |
| 这个对象**昂贵且共享**吗？（连接池、线程池、HTTP 客户端）| 由 Spring 管理（单例）| — |
| 这个对象是**本类的数据搬运工具**吗？（Mapper、Converter 依赖）| 构造器注入 | — |

---

## 2. 注入方式

### 2.1 规则表

| # | 规则 | 违规信号 |
|---|---|---|
| 1 | **只允许构造器注入** | 出现 `@Autowired` / `@Resource` / `@Inject` 在字段上 |
| 2 | 依赖字段声明为 `private final` | `private XxxService service;`（非 final）|
| 3 | 默认用 `@RequiredArgsConstructor` | 手写构造器但**不需要** `@Qualifier` |
| 4 | 需要 `@Qualifier` 时**手写构造器** | `@RequiredArgsConstructor` + 字段上的 `@Qualifier` |
| 5 | 依赖**可选**时用 `Optional<T>` / `@Nullable` | 为了可选依赖退回字段注入 |
| 6 | 单构造器**不写** `@Autowired` | 唯一构造器上多写一个 `@Autowired` |

### 2.2 为什么必须是构造器注入

| 维度 | 字段注入 `@Autowired` | 构造器注入 |
|---|---|---|
| 依赖是否必需 | ❌ 可选（漏注入 → 运行时 NPE）| ✅ 强制（编译期就报错）|
| 对象初始化完整性 | ❌ 构造器执行时依赖仍为 `null` | ✅ 构造器执行时依赖已就绪 |
| 可变性 | ❌ 无法 `final` | ✅ `final` |
| 单元测试 | ❌ 需启动 Spring 容器 | ✅ 直接 `new` + mock |
| 循环依赖 | ⚠️ 被隐藏（得到字段为 null 的半成品）| ✅ 启动即抛 `BeanCurrentlyInCreationException` |
| 依赖清单可读性 | ❌ 散落在类各处 | ✅ 集中在构造器签名里 |

> 📌 **最关键的一条**：Spring 的执行顺序是「**先解析依赖 → 再调用构造器**」（构造器注入），
> 而字段注入是「**先 new 对象 → 再反射赋值**」。
> 所以**构造器执行的那一刻，构造器注入的依赖已经是真实 Bean，字段注入的还是 `null`**。
> 依赖「构造器执行时是否可用」是二者的唯一本质差异。

**反面自检**：如果构造器里需要用某个依赖来初始化另一个字段，字段注入做不到（拿到 null），必须用构造器注入。

### 2.3 依赖清单要显式可读

```java
// ✅ 正确：依赖清单集中在构造器签名，一眼看出这个类依赖了什么
@Service
@RequiredArgsConstructor
public class PoolServiceImpl implements PoolService {
    private final StockPoolMapper stockPoolMapper;
    private final PoolMemberMapper poolMemberMapper;
    private final StockInfoService stockInfoService;
}
```

**依赖多到构造器参数过长**（如 17 个 Mapper）时，仍用构造器注入 —— 参数长是**「这个类职责过多」的信号**，
说明该拆分了，而不是说该改成字段注入。

---

## 3. Lombok `@RequiredArgsConstructor` 的适用边界

### 3.1 规则

`@RequiredArgsConstructor` **只为「`final` 且没有初始值」的字段生成参数**。

| 字段形态 | 是否生成构造器参数 |
|---|---|
| `private final XxxService service;` | ✅ 生成 |
| `private final XxxService service = new XxxService();` | ❌ 跳过（有初始值）|
| `private XxxService service;`（非 final）| ❌ 跳过 |
| `private static final int LIMIT = 500;` | ❌ 跳过（`static`）|

### 3.2 ❌ `@RequiredArgsConstructor` 会丢弃 `@Qualifier`

**这是最容易踩的坑。**

Lombok 默认只复制 `lombok.copyableAnnotations` 中配置的注解，Spring 的 `@Qualifier` **不在默认列表里**，
因此字段上写的 `@Qualifier` **不会**出现在生成的构造器参数上 → 注入时无法按名字选 Bean。

```java
// ❌ 错误：@Qualifier 被 Lombok 丢弃，注入会失败或选错 Bean
@Service
@RequiredArgsConstructor
public class PoolServiceImpl {
    @Qualifier("poolTaskExecutor")
    private final Executor executor;
}
```

**✅ 正确做法（二选一）**：

**做法 A：手写构造器**（推荐 —— `@Qualifier` 写在参数上，注入点一目了然）

```java
@Service
public class PoolServiceImpl implements PoolService {
    private final StockPoolMapper stockPoolMapper;
    private final Executor executor;

    public PoolServiceImpl(
            StockPoolMapper stockPoolMapper,
            @Qualifier("poolTaskExecutor") Executor executor) {
        this.stockPoolMapper = stockPoolMapper;
        this.executor = executor;
    }
}
```

**做法 B：在 `lombok.config` 里声明可复制注解**

```properties
lombok.copyableAnnotations += org.springframework.beans.factory.annotation.Qualifier
```

配好之后即可用 `@RequiredArgsConstructor` + 字段上的 `@Qualifier`。
> 📌 选 A 还是 B 取决于团队约定；**同一个项目里必须统一**，不要两种混用。

### 3.3 ❌ 继承场景禁止使用 `@RequiredArgsConstructor`

**父类的 `private final` 字段不会被子类构造器赋值** —— 子类根本访问不到父类的 private 字段。

```java
// ❌ 错误：父类的 final 字段永远是 null
public abstract class BaseService {
    private final SomeMapper mapper;   // 永远 null！
}

@Service
@RequiredArgsConstructor
public class MyServiceImpl extends BaseService { }
```

**继承场景必须手写构造器并显式 `super(...)`**：

```java
@Service
public class MyServiceImpl extends BaseService {
    private final OtherDependency other;

    public MyServiceImpl(SomeMapper mapper, OtherDependency other) {
        super(mapper);
        this.other = other;
    }
}
```

> 📌 若基类依赖很多，考虑把基类依赖抽成一个「参数对象」或直接改用组合替代继承。

---

## 4. `@Qualifier`：按名字选 Bean

### 4.1 为什么需要

Spring 注入默认**按类型匹配**。容器里存在**多个同类型 Bean** 时，必须用名字消歧，否则启动即抛：

```
NoUniqueBeanDefinitionException: expected single matching bean but found 3
```

### 4.2 两处配合

| 位置 | 写法 | 作用 |
|---|---|---|
| **Bean 定义处** | `@Bean("poolTaskExecutor")` | 给 Bean 起名（默认名 = 方法名）|
| **注入处** | `@Qualifier("poolTaskExecutor")` | 按名字精确筛选候选 |

**筛选规则**：先按类型得到全部候选 → 再用 `@Qualifier` 的名字过滤 → 剩余唯一者注入。

```
容器里的 Executor：
  ├─ poolTaskExecutor      ← @Qualifier 命中 ✅
  ├─ collectTaskExecutor
  └─ applicationTaskExecutor
        ↓ 名字过滤
  只剩 poolTaskExecutor → 注入
```

### 4.3 规则

| # | 规则 | 说明 |
|---|---|---|
| 1 | 同类型 Bean **超过 1 个**时，注入处**必须**写 `@Qualifier` | 否则启动失败 |
| 2 | `@Qualifier` 的值**必须**与 `@Bean("...")` 的值**完全一致** | 拼错 = 启动失败（不是静默降级）|
| 3 | `@Qualifier` 写在**构造器参数**上 | 注入点显式可见 |
| 4 | Bean 名**必须**表达职责，不用 `executor1` / `executorA` | 名字是契约 |

---

## 5. 资源型 Bean：线程池、连接池、客户端

### 5.1 核心规则

> **所有「昂贵且共享」的资源由 Spring 创建、由 Spring 销毁。**
> **业务代码只负责「用」，不负责「建」和「关」。**

### 5.2 ❌ 禁止在业务代码里 `new` 资源

```java
// ❌ 错误：线程池不随 Spring 生命周期关闭；连接池每次调用都新建
@Service
public class BadService {
    private final ExecutorService executor = Executors.newCachedThreadPool();

    @Autowired private DataSource dataSource;   // ← 且字段注入
}
```

**后果**：线程池在应用关闭时不会回收（非守护线程会阻止 JVM 退出）→ 优雅停机失败、连接泄漏。

### 5.3 ✅ 正确：用 `@Bean` 提供

```java
@Configuration
public class PoolTaskExecutorConfig {

    @Bean("poolTaskExecutor")
    public Executor poolTaskExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(4);
        executor.setMaxPoolSize(8);
        executor.setQueueCapacity(64);
        executor.setThreadNamePrefix("pool-collect-");
        executor.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
        executor.setWaitForTasksToCompleteOnShutdown(true);
        executor.setAwaitTerminationSeconds(30);
        executor.initialize();   // ★ 必须显式 initialize()，否则 Bean 里是「未启动」状态
        return executor;
    }
}
```

**关键点**：

| 要点 | 说明 |
|---|---|
| **显式 `initialize()`** | `ThreadPoolTaskExecutor` 作为 `@Bean` 返回时**不会**自动初始化，漏掉会导致提交任务时抛异常 |
| **显式设名字** | `setThreadNamePrefix` —— 排查线上问题靠线程名定位 |
| **显式设拒绝策略** | 见 `基础设施规范.md` §4.3 |
| **显式设优雅关闭** | `setWaitForTasksToCompleteOnShutdown` + `setAwaitTerminationSeconds` |
| **Bean 名表达职责** | `"poolTaskExecutor"`，不要 `"executor1"` |

### 5.4 `@Configuration` 类也用构造器注入

`@Configuration` 类会被 CGLIB 代理增强（`@Bean` 方法里的 `new` 会被改写为「从容器取」）。
字段注入在代理场景下有**初始化时序风险**，因此统一用构造器注入。

```java
@Configuration
public class WebConfig {
    /** 允许的跨域来源（构造器注入，避免字段注入在 @Configuration 中的时序问题） */
    private final List<String> allowedOrigins;

    public WebConfig(
            @Value("${app.cors.allowed-origins:http://localhost:3000}")
                    List<String> allowedOrigins) {
        this.allowedOrigins = allowedOrigins;
    }
}
```

> 📌 `@Value` 注入配置值时，也**写在构造器参数上**。

---

## 6. Bean 作用域与生命周期

### 6.1 规则

| # | 规则 | 说明 |
|---|---|---|
| 1 | **默认单例**，业务 Bean 一律不加 `@Scope` | 有状态 Bean 用单例 = 并发 bug |
| 2 | Bean 字段**不得持有请求级可变状态** | 单例 Bean 的字段会被多线程共享 |
| 3 | 请求级数据通过**方法参数**传递 | 不要塞进 Bean 字段 |
| 4 | 需要请求级状态时用 `ThreadLocal` / RequestScope，且**必须清理** | `ThreadLocal` 不清理 = 内存泄漏 |
| 5 | 静态工具类（Converter / Util）**不注册为 Bean** | 见 `../纵向分层规范/POJO规范.md` §4.2 |

### 6.2 有状态单例的反面例子

```java
// ❌ 错误：单例 Bean 持有请求级状态 → 并发请求互相污染
@Service
public class BadService {
    private String currentUserId;   // ← 所有请求共享这一个字段
}
```

**✅ 正确**：方法参数 / 局部变量。

---

## 7. AOP 代理与 `@Transactional` 自调用

### 7.1 代理是什么

类上有 `@Transactional` / `@Async` / `@Cacheable` 等注解时，Spring 会生成**代理对象**，
容器里存的是代理，代理内部持有「目标对象」。

```
调用方 ──▶ 代理对象 ──▶ 目标对象
             ↑ 拦截器在这里织入事务/异步/缓存
```

**注意**：`@Service` / `@Component` / `@RestController` **本身不触发代理**；
只有 AOP 相关注解才触发。

### 7.2 ❌ `@Transactional` 自调用失效

**同类内部直接调用方法，不经过代理 → 事务不生效。**

```java
@Service
public class PoolServiceImpl {
    private final PoolOperationMapper operationMapper;

    @Transactional(rollbackFor = Exception.class)
    public void outer() {
        this.inner();          // ❌ 直接调用，不走代理 → 事务不生效
    }

    @Transactional(rollbackFor = Exception.class)
    public void inner() { ... }
}
```

**✅ 正确做法（二选一）**：

| 做法 | 说明 |
|---|---|
| **拆到另一个 Bean** | 把 `inner` 移到独立 Service，由另一个 Bean 调用 → 走代理 |
| **注入自己** | `private final PoolServiceImpl self;`（注意：注入自己拿到的是代理，需谨慎使用）|

> 📌 **优先拆到另一个 Bean** —— 「注入自己」依赖 Spring 的早期引用机制，可读性差且容易误用。

### 7.3 异步派发天然绕过代理

用线程池派发任务时，任务在**另一个线程**里执行，**不在原事务内**：

```java
@Transactional(rollbackFor = Exception.class)
public PoolOperationCreateVO createOp(...) {
    operationMapper.insert(op);
    executor.execute(() -> runCollectOperation(op.getId(), ...));  // ★ 事务外执行
    return result;
}
```

这是**正确且推荐**的结构：事务内只落库，远程调用放事务外。
（详见 `基础设施规范.md` §4.4）

---

## 8. 决策流程

```
要注入一个依赖
   │
   ├─ 它是「昂贵且共享」的资源？（线程池 / 连接池 / HTTP 客户端）
   │      └─ 是 → 用 @Bean 提供，注入处按需要加 @Qualifier
   │
   ├─ 它是可选的？
   │      ├─ 否 → private final + @RequiredArgsConstructor
   │      └─ 是 → private final Optional<T> / @Nullable + 构造器注入
   │             ⚠️ 不许退回字段注入
   │
   └─ 需要 @Qualifier（同类型 Bean 多个）？
          ├─ 否 → @RequiredArgsConstructor
          └─ 是 → 手写构造器（@Qualifier 写在参数上）
                 ⚠️ @RequiredArgsConstructor 会丢弃 @Qualifier
```

**继承场景** → 一律手写构造器 + `super(...)`。

---

## 9. Code Review 清单

| # | 检查项 | 违规信号 |
|---|---|---|
| 1 | 有字段注入？ | `@Autowired` / `@Resource` / `@Inject` 出现在字段上 |
| 2 | 依赖字段是 `final`？ | `private XxxService service;`（非 final）|
| 3 | 单构造器上有多余 `@Autowired`？ | 唯一构造器标了 `@Autowired` |
| 4 | `@Qualifier` 被 Lombok 丢弃？ | `@RequiredArgsConstructor` + 字段上的 `@Qualifier` |
| 5 | `@Qualifier` 的值与 `@Bean("...")` 一致？ | 名字拼错 / Bean 名是 `executor1` 这类无意义名 |
| 6 | 同类型 Bean 多个但注入处没 `@Qualifier`？ | 启动期 `NoUniqueBeanDefinitionException` |
| 7 | 业务代码里 `new` 线程池 / 连接池 / HTTP 客户端？ | `Executors.new*` / `new RestTemplate()` |
| 8 | `ThreadPoolTaskExecutor` 漏 `initialize()`？ | `@Bean` 方法里没调 |
| 9 | 线程池漏设拒绝策略 / 线程名 / 优雅关闭？ | 只设了 `corePoolSize` |
| 10 | 单例 Bean 持有请求级可变状态？ | Bean 里有非 `final` 的业务字段 |
| 11 | 继承场景用了 `@RequiredArgsConstructor`？ | 子类 `@RequiredArgsConstructor` + 父类 `private final` 字段 |
| 12 | `@Transactional` 自调用？ | 同类内 `this.xxx()` 调用带 `@Transactional` 的方法 |
| 13 | 静态工具类被注册成 Bean？ | Converter / Util 上有 `@Component` |
| 14 | `@Value` 写在字段上？ | 字段注入配置值 |

---

## 10. 技术前提（环境事实，长期有效）

| 项 | 值 | 来源 |
|---|---|---|
| 框架 | Spring Boot 3.2.5 / Spring Framework 6.x | `pom.xml` |
| 构造器自动注入 | **单构造器无需 `@Autowired`**（Spring 4.3+）| Spring 官方行为 |
| 循环依赖 | **默认禁止**（`spring.main.allow-circular-references=false`）| Spring Boot 2.6+ 默认 |
| Lombok | 1.18.34 | `pom.xml` |
| Lombok 注解处理器 | `maven-compiler-plugin` 的 `annotationProcessorPaths` | 父 `pom.xml` |
| 编译参数 | `-parameters` 已开启（`<parameters>true</parameters>`）| 父 `pom.xml` → `maven-compiler-plugin` |
| 线程池 Bean | `ThreadPoolTaskExecutor`，`@Bean("poolTaskExecutor")` | `attribution-user/config/PoolTaskExecutorConfig.java` |
| `ObjectMapper` | Spring 容器管理的单例（含 `SNAKE_CASE` 配置）| `application.yml` |
| `StringRedisTemplate` | Spring Boot 自动配置（Lettuce），**禁止** `new` | `attribution-auth/pom.xml` |

> 📌 **`-parameters` 与 `@Qualifier` 是两件事**：
> `-parameters` 影响 `@PathVariable` / `@RequestParam` 的**隐式参数名解析**；
> `@Qualifier` 影响**选哪个 Bean**。前者已开启不代表后者会生效。

---

## 11. 与其他文档的关系

| 文档 | 管什么 |
|---|---|
| **`依赖注入与Bean规范.md`（本文）** | **怎么注入依赖、Bean 谁创建、生命周期、AOP 代理陷阱** |
| `../纵向分层规范/Service层规范.md` | Service 层该做什么、事务边界、跨模块协作 |
| `../纵向分层规范/Controller层规范.md` | Controller 的协议适配、参数绑定、响应封装 |
| `../纵向分层规范/POJO规范.md` | Converter 为何是静态工具类（不注册为 Bean）|
| `../横切技术规范/基础设施规范.md` | 线程池 / 连接池 / Redis / HTTP 客户端的**参数与降级** |
| `../横切技术规范/异常与响应规范.md` | Bean 创建失败 / 注入失败时的异常表达 |
| `../审计与整改/` | **历史快照**：某次整改的实测数字，勿作为规范依据 |

> 分工：**「这段逻辑放哪层」看纵向分层规范；「资源怎么管、依赖怎么注入」看横切规范。**

---

> **本文档只写规则，不含任何现状计数。**
> 新增 Bean 或修改注入方式时，请按 §9（Code Review 清单）与 §8（决策流程）自查。
