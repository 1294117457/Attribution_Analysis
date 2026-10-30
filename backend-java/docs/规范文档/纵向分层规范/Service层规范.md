# Service 层规范（业务编排层）

> 适用范围：`backend-java` 全部 Maven 模块
> 核心原则：**Service 是「业务编排层」，不是「数据访问层」。**
> 同层文档：`Controller层规范.md`（协议适配）、`Mapper层规范.md`（持久化）、`POJO规范.md`（数据形状）

---

## 0. 一句话结论
> **Service 只做三件事：① 编排业务规则 ② 调用 Mapper ③ 转换 PO→VO。**
> **凡是「怎么查」「怎么存」「怎么拼 SQL」——全部属于 Mapper。**

---

## 1. 职责速查

```
┌──────────────────────────────────────────────────────────────┐
│ Controller  HTTP 协议、参数绑定、@Valid 校验、组装 ApiResponse │
│   ↕ DTO / VO                                                │
├──────────────────────────────────────────────────────────────┤
│ Service     ★ 业务编排层 ★                                    │
│             · 业务规则校验（需查库才能判定的规则）             │
│             · 调用一个或多个 Mapper                           │
│             · PO → VO 转换（调 Converter）                    │
│             · 事务边界（@Transactional）                       │
│             · 跨模块协作（调其他 Service / 外部 API）          │
│   ↕ PO / BO                                                 │
├──────────────────────────────────────────────────────────────┤
│ Mapper      ★ 持久化唯一入口 ★（见 Mapper层规范.md）          │
└──────────────────────────────────────────────────────────────┘
```

| 层 | 唯一职责 | 判断标准 |
|---|---|---|
| **Controller** | 协议适配 | 代码里出现 `HttpServletRequest` / `@RequestParam` / 状态码 |
| **Service** | 业务编排 | 代码里出现 `if` 判断业务规则、多个 Mapper 协作、`@Transactional` |
| **Mapper** | 数据存取 | 代码里只有查询条件与结果映射，无业务判断 |
| **Converter** | 数据搬运 | 代码里只有 `po.getXxx()` → `vo.setXxx()` |
| **Util** | 无状态计算 | 代码里只有数学/指标计算，无 IO |

> ⚠️ **反向自检**：写完 Service 后若发现里面有「怎么查」的细节（列名、JOIN、SQL 片段），说明写错层了。

---

## 2. Service 层「该做」什么

### 2.1 业务规则校验（Service 的第一职责）

只有**需要查库才能判定**的规则才在 Service 做。

```java
// ✅ 正确：业务规则 + 查库判定
public TokenVO login(LoginRequest request) {
    UserPO user = userMapper.selectOne(
            new LambdaQueryWrapper<UserPO>().eq(UserPO::getEmail, request.getEmail()));
    if (user == null || !passwordEncoder.matches(request.getPassword(), user.getPasswordHash()))
        throw new BusinessException(401, "用户名或密码错误");
    if (!Boolean.TRUE.equals(user.getIsActive()))
        throw new BusinessException(403, "账号已停用");
    // ...
}
```

| 规则类型 | 归属 | 例子 |
|---|---|---|
| **格式**（长度/正则/范围）| **DTO `@Valid`** | `@Size(max = 64)`、`@Pattern` |
| **存在性**（查库判定）| **Service** | 邮箱是否已注册、池是否存在 |
| **状态冲突** | **Service** | 默认池不能删、已有运行中任务 |
| **一致性**（多表）| **Service** | 用户名与密码匹配、验证码与缓存一致 |

> **分界线**：不需要查库就能判定的 → 交给 `@Valid` 注解；需要查库的 → Service 里 `if`。

### 2.2 编排多个 Mapper

Service 的核心价值是**协调**多个数据源完成一个业务动作。

```java
// ✅ 正确：编排 3 个 Mapper 完成一个业务动作
@Override
public PoolVO patch(int id, PoolUpdateRequest request) {
    StockPoolPO pool = requirePool(id);              // ① 查主表
    if (request.getName() != null) pool.setName(request.getName());
    // ...
    stockPoolMapper.updateById(pool);                // ② 更新
    return PoolConverter.toVO(pool, countMembers(id)); // ③ 转换 + 统计
}
```

### 2.3 事务边界

**事务注解只能加在 Service**，Mapper 加事务没有意义（Mapper 方法在 Service 的事务里执行）。

```java
// ✅ 正确：多表写操作加事务
@Transactional(rollbackFor = Exception.class)
@Override
public void delete(int id) {
    poolMemberMapper.delete(new LambdaQueryWrapper<PoolMemberPO>().eq(PoolMemberPO::getPoolId, id));
    stockPoolMapper.deleteById(id);
}
```

| 规则 | 说明 |
|---|---|
| 加在 **public** 方法上 | Spring AOP 自调用失效，`private`/`self.` 调用不加事务 |
| `rollbackFor = Exception.class` | 默认只回滚 `RuntimeException`，受检异常不回滚 |
| **只读方法不加** | 加了徒增开销，无意义 |
| 事务方法内**禁止**远程调用 | 会长时间持有数据库连接（见 §4.2） |

### 2.4 跨模块协作

**跨模块调用 Service，不调 Mapper。**

```java
// ✅ 正确：attribution-user 调 attribution-market 的 Service
private final StockInfoService stockInfoService;   // 而非 StockInfoMapper
```

### 2.5 PO → VO 转换

**转换在 Service 层发生**（Mapper 只取数不认识 VO，Controller 只管协议不认识 PO）。

```java
// ✅ 正确
PO po = mapper.selectById(id);
VO vo = PoolConverter.toVO(po, memberCount);
return vo;
```

### 2.6 外部 API 调用与容错

调用 Python collector 这类外部系统时，**容错、降级、重试策略属于 Service**。

```java
// ✅ 正确：单条失败不影响整体
for (String indexCode : indexCodes) {
    try {
        Object data = collectorService.query("concept_minute", Map.of("index_code", indexCode));
        // ...
    } catch (Exception ignored) {
        // 单个概念取不到时跳过，不影响其余
    }
}
```

### 2.7 内存计算与算法编排

指标计算、排序、分桶等**纯计算**逻辑放 Service 或 Util（放 Util 更好）。

```java
// ✅ 正确：调用 Util 做指标计算，Service 负责编排
var indicators = IndicatorUtil.calculate(closePrices, highPrices, lowPrices);
var summaryMap = IndicatorUtil.summarize(closePrices, changes, indicators);
result.setSummary(MarketConverter.toSummaryVO(summaryMap));
```

### 2.8 分页与「取前 N 行」

**分页是 Service 的职责，但要 MyBatis-Plus 的 `Page<T>`，不要手写 OFFSET。**

```java
// ✅ 正确：MyBatis-Plus 分页（需已注册 PaginationInnerInterceptor）
var pageParam = new Page<StockPoolPO>(query.getPage(), query.getPageSize());
List<StockPoolPO> pools = stockPoolMapper.selectPage(pageParam, wrapper).getRecords();
return PageResult.of(total, list, query.getPage(), query.getPageSize());
```

**「取最近 N 行」用 `TopN` 辅助类**，它内部用 `Page<>(1, n)` 复用分页插件，Service 层不出现 SQL 字符串：

```java
// ✅ 正确：取前 N 条
List<TechKlinePO> rows = TopN.query(techKlineMapper, wrapper, limit);

// ✅ 正确：取最新一条（等价 ORDER BY x DESC LIMIT 1）
List<TechKlinePO> latest = TopN.latest(mapper, wrapper);
```

> ⚠️ **前置条件**：分页插件必须已注册，否则 `selectPage` 不会追加 LIMIT，会把全表数据拉回内存。
> 插件的 `maxLimit` 必须 ≥ 业务允许的最大单次取数，否则会**静默丢数据**。详见 §8 技术前提。

---

## 3. Service 层「不该做」什么

### 3.1 ❌ 禁止：任何形式的 SQL

```java
// ❌ 裸 JDBC
try (Connection conn = dataSource.getConnection();
     Statement stmt = conn.createStatement()) {
    ResultSet rs = stmt.executeQuery("SELECT ... WHERE symbol='" + symbol + "'");
}

// ❌ 注解 SQL
@Select("SELECT * FROM tech_kline_daily WHERE symbol = #{symbol}")
List<TechKlinePO> selectBySymbol(@Param("symbol") String symbol);

// ❌ MyBatis-Plus 的原生 SQL 片段
new QueryWrapper<TechKlinePO>().eq("symbol", symbol).last("LIMIT " + limit);
```

**`.last()` / `.apply()` / `.inSql()` / `.having()` / `.setSql()` 都是 SQL 片段**，写在 Service 里等于把 SQL 藏在了业务代码中。

| 片段 | 风险 | 替代方案 |
|---|---|---|
| `.last("LIMIT n")` | 绕过分页插件；SQL 散落各处 | `TopN.query(mapper, wrapper, n)` / `Page<T>` 分页 |
| `.apply("...")` | 拼接字符串，**易 SQL 注入** | `#{}` 绑定 |
| `.inSql("...")` | 拼接子查询，**易 SQL 注入** | `.in(PO::getCol, list)` |
| `.having("...")` | 聚合条件难以维护 | XML `<where>` / `<having>` |
| `.setSql("...")` | 绕过字段白名单 | 用 PO 字段 set |

> 📌 本节只列 Service 层的红线。**Mapper 该怎么写（XML、批量、聚合、视图行、分页）见 `Mapper层规范.md`。**

### 3.2 ❌ 禁止：查询条件用字符串列名

```java
// ❌ 错误：列名写死为字符串，编译期无法检查，拼错不报错
new QueryWrapper<TechKlinePO>().eq("symbol", symbol).ge("date", startDate);

// ✅ 正确：Lambda 引用，编译期校验，重构安全
new LambdaQueryWrapper<TechKlinePO>()
        .eq(TechKlinePO::getSymbol, symbol)
        .ge(TechKlinePO::getDate, startDate);
```

> **判定标准**：`.eq("列名", ...)` 出现即为违规。`LambdaQueryWrapper` 的 `::getXxx` 是合规的。

### 3.3 ❌ 禁止：循环内查库（N+1）

```java
// ❌ 错误：N 次成员 → N 次 count + N 次 selectById
for (PoolMemberPO membership : memberships) {
    StockPoolPO pool = stockPoolMapper.selectById(membership.getPoolId());
    if (pool != null) poolVOs.add(PoolConverter.toVO(pool, countMembers(pool.getPoolId())));
}

// ✅ 正确：一次批量查询
List<StockPoolPO> pools = stockPoolMapper.selectBatchIds(poolIds);
```

| 场景 | 错误做法 | 正确做法 |
|---|---|---|
| 取关联实体 | 循环 `selectById` | `selectBatchIds(ids)` |
| 统计数量 | 循环 `selectCount` | 一次 `GROUP BY` 聚合（XML）|
| 查已存在项 | 循环 `selectCount` | 一次 `IN` 查询（XML）|
| 取多字段 | 循环查多张表 | 一次联表 / CTE 聚合（XML）|

### 3.4 ❌ 禁止：吞异常

```java
// ❌ 错误：异常被完全吞掉，故障静默，线上无法排查
try {
    ...
} catch (Exception ignored) {
}

// ❌ 更糟：catch 后返回空数据，前端拿到「没有数据」而非「查询失败」
try {
    return mapper.selectOne(wrapper);
} catch (Exception e) {
    return null;
}
```

**允许吞异常的唯一场景**：外部系统（collector）不可用且**有明确的降级兜底**（如回退到本地缓存、跳过该条并继续处理其余）。

```java
// ✅ 可接受：外部依赖降级，注释说明原因
try {
    entity = conceptMapper.selectOne(...);
} catch (Exception ignored) {
    // 查不到元信息不影响 K 线返回
}
```

> 📌 **要求**：每个 `catch (Exception ignored)` 必须有注释说明降级语义，否则视为违规。

### 3.5 ❌ 禁止：Service 接口出现 PO 或 Map

```java
// ❌ 错误
public List<StockInfoPO> list();
public Object detail(String name);
public Map<String, Object> board(String type, String sort);

// ✅ 正确
public PageResult<StockInfoVO> page(StockPanelQuery query);
public ConceptDetailVO detail(String conceptName);
public PageResult<ConceptBoardItemVO> board(ConceptBoardQuery query);
```

| 类型 | 是否允许 | 理由 |
|---|---|---|
| **PO** | ❌ 禁止 | 泄漏表结构、含敏感字段、破坏解耦 |
| **裸 `Map`** | ❌ 禁止 | 无类型约束、字段名靠手写、IDE 无法补全 |
| **`Map<String, XxxVO>`** | ⚠️ 有条件 | 仅当**前端契约本身是动态 key**（如 `Record<string, ConceptSnapshot>`）|
| **DTO / VO** | ✅ 正确 | — |

### 3.6 ❌ 禁止：在 Service 里做 HTTP 协议细节

```java
// ❌ 错误：Service 关心状态码
public ApiResponse<?> doSomething() { ... }
```

`ApiResponse` 属于 Controller 层。Service 抛 `BusinessException`，由 `GlobalExceptionHandler` 统一转 HTTP 响应。

### 3.7 ❌ 禁止：Service 里 new 线程池 / 持有可变静态状态

```java
// ❌ 错误：每个 Service 实例一个线程池，且不随 Spring 生命周期关闭
private final Executor executor = Executors.newCachedThreadPool();
```

线程池应由 Spring 管理（`@Bean` + `@Async`），Service 只声明 `@Async` 方法。

### 3.8 ❌ 禁止：Service 承担数据搬运职责

Mapper 已返回 PO，Service 应**直接使用**，不要在 Service 里做「PO → 中间 Map → VO」的多余中转。

```java
// ❌ 多余中转
Map<String, Object> basic = new LinkedHashMap<>();
basic.put("latest_close", latest.getClose());
basic.put("total_mv", latest.getTotalMv());
// ... 再从 Map 取出来 set 到 VO

// ✅ 直接用 PO
stockVO.setLatestClose(latest.getClose());
stockVO.setTotalMv(latest.getTotalMv());
```

---

## 4. 决策流程（写代码时照着走）

### 4.1 「这个逻辑放哪？」

```
我要写一段逻辑
  │
  ├─ 是 HTTP 协议相关（状态码 / header / 参数绑定）？ → Controller
  │
  ├─ 是纯计算（指标 / 排序 / 格式化），无 IO？      → Util
  │
  ├─ 是数据搬运（PO.getXxx → VO.setXxx）？          → Converter
  │
  ├─ 需要查库吗？
  │   ├─ 否 → Service（业务规则校验）或 Controller（格式校验）
  │   └─ 是
  │       ├─ 单表简单条件          → Service 调 Mapper 的 LambdaQueryWrapper
  │       ├─ 联表 / 聚合 / 动态列  → Service 调 Mapper 的 XML 方法
  │       └─ 分页                 → Service 调 Mapper 的分页方法（Page<T>）
  │
  └─ 是编排（调多个 Mapper / 调其他 Service / 调外部 API）？ → Service
```

### 4.2 「Service 里能不能调外部 API？」

可以，但要注意：

| 约束 | 原因 |
|---|---|
| **不要在 `@Transactional` 方法内调远程** | 远程耗时 3s → 数据库连接被占 3s，连接池耗尽 |
| 外部调用要**独立容错** | collector 挂掉不能让主流程 500 |
| 批量外部调用要**限流** | 逐个调 collector，100 个概念 = 100 次往返 |

**推荐做法**：把外部调用挪到 `@Transactional` 方法**之外**，或用 `TransactionSynchronizationManager` 在事务提交后再调。

---

## 5. Service 方法模板

### 5.1 简单查询（单表）

```java
@Override
public StockInfoVO get(String symbol) {
    StockInfoPO stock = stockInfoMapper.selectOne(
            new LambdaQueryWrapper<StockInfoPO>().eq(StockInfoPO::getSymbol, symbol));
    if (stock == null) throw new BusinessException(404, "股票不存在");
    return MarketConverter.toStockInfoVO(stock);
}
```

**要点**：查库 → 判空抛业务异常 → 转换返回。三步，不多不少。

### 5.2 分页查询

```java
@Override
public PageResult<PoolVO> list(PoolQuery query) {
    var wrapper = new LambdaQueryWrapper<StockPoolPO>();
    if (!query.isIncludeArchived()) wrapper.eq(StockPoolPO::getIsArchived, false);

    // count 查询不能带 orderBy（PostgreSQL: column must appear in the GROUP BY）
    long total = stockPoolMapper.selectCount(wrapper);
    wrapper.orderByAsc(StockPoolPO::getId);

    var pageParam = new Page<StockPoolPO>(query.getPage(), query.getPageSize());
    List<StockPoolPO> pools = stockPoolMapper.selectPage(pageParam, wrapper).getRecords();

    List<PoolVO> list = new ArrayList<>();
    for (StockPoolPO pool : pools) list.add(PoolConverter.toVO(pool, countMembers(pool.getId())));
    return PageResult.of(total, list, query.getPage(), query.getPageSize());
}
```

> ⚠️ 这里的 `countMembers(pool.getId())` 在循环内 → N+1。正确做法见 §3.3。

### 5.3 多表写（事务）

```java
@Transactional(rollbackFor = Exception.class)
@Override
public void delete(int id) {
    poolMemberMapper.delete(new LambdaQueryWrapper<PoolMemberPO>().eq(PoolMemberPO::getPoolId, id));
    stockPoolMapper.deleteById(id);
}
```

### 5.4 编排多数据源

```java
@Override
public StockAnalysisVO analysis(String symbol, int days) {
    StockInfoPO stock = stockInfoMapper.selectOne(
            new LambdaQueryWrapper<StockInfoPO>().eq(StockInfoPO::getSymbol, symbol));
    if (stock == null) throw new BusinessException(404, "股票不存在");

    List<TechKlinePO> klines = techKlineMapper.selectList(...);
    var indicators = IndicatorUtil.calculate(closePrices, highPrices, lowPrices);
    var summaryMap = IndicatorUtil.summarize(closePrices, changes, indicators);

    StockAnalysisVO result = new StockAnalysisVO();
    result.setStock(MarketConverter.toAnalysisStockVO(stock));
    result.setSummary(MarketConverter.toSummaryVO(summaryMap));
    result.setKlines(...);
    return result;
}
```

---

## 6. Code Review 清单

| # | 检查项 | 违规信号 |
|---|---|---|
| 1 | 有裸 JDBC？ | `DataSource` / `Connection` / `Statement` / `ResultSet` |
| 2 | 有注解 SQL？ | `@Select` / `@Update` / `@Insert` / `@Delete` |
| 3 | 有原生 SQL 片段？ | `.last()` / `.apply()` / `.inSql()` / `.having()` / `.setSql()` |
| 4 | 列名是字符串？ | `.eq("symbol", ...)` 而非 `.eq(PO::getSymbol, ...)` |
| 5 | 循环里查库？ | `for` 循环体内出现 `mapper.` 调用 |
| 6 | 吞异常？ | `catch (Exception ignored)` 且无降级注释 |
| 7 | 接口暴露 PO？ | 方法签名出现 `XxxPO` |
| 8 | 接口暴露裸 Map？ | 方法签名出现 `Map<String, Object>`（动态 key 契约除外）|
| 9 | Service 返回 HTTP 对象？ | 方法签名出现 `ApiResponse` / `ResponseEntity` |
| 10 | Service 自己 new 线程池？ | `Executors.new*` |
| 11 | 多表写没事务？ | 多个 `insert`/`update`/`delete` 无 `@Transactional` |
| 12 | 跨模块注入 Mapper？ | 注入了其他模块的 `XxxMapper` |
| 13 | 死依赖？ | 注入的 Mapper 从未被调用 |
| 14 | 手动 `new ObjectMapper`？ | 应注入 Spring 管理的 Bean；静态 Converter 则作为参数传入（见 `POJO规范.md` §4.3.1）|
| 15 | count 带 orderBy？ | `selectCount` 的 wrapper 含 `orderBy` |

---

## 7. 新增 Service 的检查清单

- [ ] 没有 `DataSource` / `Statement` / `ResultSet` / `@Select`
- [ ] 没有 `.last()` / `.apply()` / `.inSql()` / `.having()` / `.setSql()`
- [ ] 所有列名用 `PO::getXxx` 引用，不是字符串
- [ ] 循环体内没有 Mapper 调用（N+1）
- [ ] `catch` 块要么不吞，要么有明确降级注释
- [ ] 接口方法签名里没有 `XxxPO` / 裸 `Map` / `ApiResponse`
- [ ] 多表写操作加了 `@Transactional(rollbackFor = Exception.class)`
- [ ] 没有 `Executors.new*`（线程池交给 Spring）
- [ ] 跨模块调的是 Service 不是 Mapper
- [ ] 注入的依赖全部被用到
- [ ] PO→VO 转换走 `Converter`，不手写一堆 `set`
- [ ] 业务规则错误抛 `BusinessException`，不用 `RuntimeException`
- [ ] `selectCount` 的 wrapper 不含 `orderBy`

---

## 8. 技术前提（环境事实，长期有效）

> 这些是**约定与配置**，不随代码改动而失效，因此放在规范里。
> 变更时需同步更新本表。

| 项 | 值 | 来源 |
|---|---|---|
| ORM | MyBatis-Plus 3.5.7 | `pom.xml` |
| 数据库 | PostgreSQL | `spring.datasource.url` |
| 分页插件 | `PaginationInnerInterceptor`，`maxLimit = 10000`，`overflow = false` | `MybatisPlusConfig` |
| 攻击防护 | `BlockAttackInnerInterceptor`（阻断全表 update/delete）| `MybatisPlusConfig` |
| 取前 N 行 | `TopN.query(mapper, wrapper, n)` / `TopN.latest(mapper, wrapper)` | `attribution-common/mybatis/TopN.java` |
| XML Mapper 位置 | `classpath*:/mapper/**/*.xml` | `application.yml` |
| 统一响应 | `{code, message, data}` | `ApiResponse` |
| 业务异常 | `BusinessException(code, message)`，`code` 即 HTTP 状态码 | `attribution-common/exception/` |
| 全局异常处理 | `GlobalExceptionHandler`：业务异常 → 对应状态码；校验失败 → 422；兜底 → 500 | `attribution-common/exception/` |
| 事务注解 | `@Transactional(rollbackFor = Exception.class)` | — |
| 线程池 | 由 Spring `@Bean` 提供，Service 不自己 new | 各模块 `config/` |
| 依赖注入 | 构造器注入（`@RequiredArgsConstructor`；需 `@Qualifier` 时手写构造器）| `../横切技术规范/依赖注入与Bean规范.md` |
| Jackson 命名策略 | `SNAKE_CASE` | `spring.jackson.property-naming-strategy` |

---

## 9. 与其他文档的关系

| 文档 | 管什么 |
|---|---|
| **`Service层规范.md`（本文）** | Service 层**该做什么、不该做什么**、职责边界、Code Review 清单 |
| `Controller层规范.md` | Controller 层**路径、参数绑定、校验、响应封装**、豁免场景 |
| `POJO规范.md` | DTO / PO / VO / BO 的**定义规范**：字段类型、校验注解、Converter 写法 |
| `Mapper层规范.md` | **持久化唯一入口**：XML 写法、批量与聚合、视图行定义、分页 |
| `../横切技术规范/依赖注入与Bean规范.md` | **依赖注入方式、Bean 创建与生命周期、AOP 代理陷阱** |
| `../审计与整改/` | **历史快照**：某次整改的实测数字，勿作为规范依据 |

> 四份文档的分工：**「用什么形状传递数据」看 `POJO规范.md`；「哪层负责什么」看三份分层规范。**
> **「依赖怎么注入、Bean 谁创建」看 `../横切技术规范/依赖注入与Bean规范.md`。**

---

> **本文档只写规则，不含任何现状计数。**
> 后续新增代码请按 §6（Code Review 清单）与 §7（新增 Service 检查清单）自查，
> 每项改完跑 `mvn compile` + `npx vue-tsc --noEmit` 验证。
