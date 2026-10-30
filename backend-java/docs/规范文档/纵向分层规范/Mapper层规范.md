# Mapper 层规范（持久化唯一入口）

> 适用范围：`backend-java` 全部 Maven 模块的 `mapper/` 包与 `resources/mapper/*.xml`
> 核心原则：**Mapper 只做「数据存取」——把查询条件翻译成 SQL，把结果集翻译成 PO / Row。不含任何业务判断。**
> 同层文档：`Service层规范.md`（业务编排）、`Controller层规范.md`（协议适配）、`POJO规范.md`（数据形状）

---

## 0. 一句话结论
> **凡是「怎么查」「怎么存」「怎么拼 SQL」——全部属于 Mapper。**
> Mapper 是持久化的**唯一入口**：Service 禁止出现 JDBC，Controller 禁止出现 Mapper。

---

## 1. 职责速查

```
┌──────────────────────────────────────────────────────────────┐
│ Service     业务编排（见 Service层规范.md）                     │
│   ↕ PO / Row                                                  │
├──────────────────────────────────────────────────────────────┤
│ Mapper      ★ 持久化唯一入口 ★                                │
│             · 单表 CRUD → BaseMapper / LambdaQueryWrapper     │
│             · 联表 / 聚合 / 动态列 → XML Mapper                │
│             · 批量 IN / CTE → XML Mapper                      │
│             · count 与 list 用同一个 <where> 片段              │
│             · 返回 PO / 视图行 Row / 聚合标量                  │
│   ↕                                                           │
├──────────────────────────────────────────────────────────────┤
│ DB          表                                                  │
└──────────────────────────────────────────────────────────────┘
```

| 层 | 唯一职责 | 判断标准 |
|---|---|---|
| **Service** | 业务编排 | 有查库后的 `if`、多 Mapper 协作、`@Transactional` |
| **Mapper** | 数据存取 | 代码里只有查询条件与结果映射，**无业务判断** |
| **Converter** | 数据搬运 | `po.getXxx()` → `vo.setXxx()` |

---

## 2. Mapper 层「该做」什么

### 2.1 接口形态

```java
package com.attribution.market.mapper;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import com.attribution.market.entity.StockInfoPO;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;

@Mapper
public interface StockInfoMapper extends BaseMapper<StockInfoPO> {

    /**
     * 批量取股票所属自选池（跨表联查 stock_pool_members + stock_pools）。
     *
     * @param symbols 股票代码列表
     * @return 视图行：symbol / pool_id / name / pool_type
     */
    List<PoolMembershipRow> selectPoolMemberships(@Param("symbols") List<String> symbols);
}
```

| 规则 | 说明 |
|---|---|
| **一个 Mapper 对应一张表的 PO** | 不跨领域，不跨模块 |
| **继承 `BaseMapper<XxxPO>`** | 单表 CRUD 直接可用，无需自己写 |
| **加 `@Mapper`** | 与 `@MapperScan` 并存不冲突，两者都是注册途径 |
| **方法必须有 Javadoc** | `@param` / `@return` 齐全，说明这条查询的语义边界 |
| **参数必须加 `@Param`** | 多个参数时**必须**加，否则 XML 里只能按 `param1/param2/arg0` 取 |
| **新模块要加 `@MapperScan`** | `AttributionApp` 的 `@MapperScan` 必须包含新模块的 mapper 包 |

> ⚠️ `application.yml` 的 `mapper-locations: classpath*:/mapper/**/*.xml` 是启用 XML Mapper 的前提，缺失则 XML 方法在启动时报
> `Invalid bound statement (not found)`。

### 2.2 能力边界：什么该写在 Mapper，什么不该

| 查询形态 | 归属 | 写法 |
|---|---|---|
| 单表、按主键 | Mapper | `selectById` / `deleteById` / `updateById` |
| 单表、多条件 | **Service** 用 `LambdaQueryWrapper` 组装 | `mapper.selectList(wrapper)` |
| 单表 + 分页 | **Service** 用 `Page<T>` | `mapper.selectPage(pageParam, wrapper)` |
| 单表 + 排序取前 N | **Service** 用 `TopN` | `TopN.query(mapper, wrapper, n)` |
| **联表**（≥2 表 JOIN）| **Mapper** | XML `<select>` |
| **聚合**（COUNT / GROUP BY / 统计）| **Mapper** | XML `<select>` |
| **批量 IN 查询** | **Mapper** | XML `<select>` + `<foreach>` |
| **CTE / 复杂统计** | **Mapper** | XML `<select>` + `WITH` |
| **动态表名 / 动态列名** | **Mapper** | 白名单枚举 + `<choose>`，**禁止拼用户输入** |

> **判定口诀**：能靠 `LambdaQueryWrapper` 一句话说清楚的 → 不写 Mapper 方法；
> 需要 JOIN / GROUP BY / 多次往返的 → 写 XML。

### 2.3 XML Mapper 规范

#### 2.3.1 文件与命名

| 项 | 规范 |
|---|---|
| **位置** | `attribution-<module>/src/main/resources/mapper/XxxMapper.xml`（与 Mapper 接口**同名**）|
| **namespace** | 接口全限定名，如 `com.attribution.market.mapper.StockInfoMapper` |
| **`<select id>`** | **必须与方法名完全一致** |
| **resultType** | 全限定名（独立 Row 类用 `...mapper.row.XxxRow`；接口内部类用 `...Mapper$XxxRow`）|
| **参数绑定** | 一律 `#{}`，**禁止 `${}`** |

#### 2.3.2 标准骨架

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN"
    "http://mybatis.org/dtd/mybatis-3-mapper.dtd">
<mapper namespace="com.attribution.user.mapper.PoolMemberMapper">

    <!-- 批量统计各池成员数（一次查询替代 Service 层逐池 count，消除 N+1） -->
    <select id="selectMemberCounts"
            resultType="com.attribution.user.mapper.row.PoolMemberCountRow">
        SELECT pool_id, COUNT(*) AS member_count
        FROM stock_pool_members
        WHERE pool_id IN
        <foreach collection="poolIds" item="poolId" open="(" separator="," close=")">
            #{poolId}
        </foreach>
        GROUP BY pool_id
    </select>

</mapper>
```

#### 2.3.3 `<foreach>` 必须防空集合

`<foreach collection="x" open="(" ...>` 在集合为空时会生成 `IN ()` —— **PostgreSQL 语法错误**。

```xml
<!-- ❌ 错误：symbols 为空时生成 IN () -->
WHERE m.symbol IN
<foreach collection="symbols" item="symbol" open="(" separator="," close=")">
    #{symbol}
</foreach>

<!-- ✅ 正确一：XML 内判空（NULL 走恒假条件）—— 推荐，双保险 -->
WHERE m.symbol IN
<choose>
    <when test="symbols != null and symbols.size() > 0">
        <foreach collection="symbols" item="symbol" open="(" separator="," close=")">
            #{symbol}
        </foreach>
    </when>
    <otherwise>NULL</otherwise>
</choose>

<!-- ✅ 正确二：Service 侧前置 return —— 也应保留，防止无谓往返 -->
```

> 📌 **双保险原则**：XML 内 `<choose>` 兜底 + Service 侧 `isEmpty()` 前置 return，两者都要有。
> 只做 Service 侧，一旦新增调用方忘记判空就会 500。

#### 2.3.4 count 与 list 必须共用 `<where>`

过滤条件不一致会导致「总数 100、列表 0 条」这类诡异分页 bug。

```xml
<!-- ✅ 正确：抽成 <sql> 片段复用 -->
<sql id="stockFilter">
    <where>
        <if test="industry != null and industry != ''">AND industry = #{industry}</if>
        <if test="market != null and market != ''">AND market = #{market}</if>
    </where>
</sql>

<select id="countStocks" resultType="long">
    SELECT COUNT(*) FROM fundamental_stock_info
    <include refid="stockFilter"/>
</select>

<select id="selectStocks" resultType="...row.StockInfoRow">
    SELECT * FROM fundamental_stock_info
    <include refid="stockFilter"/>
    ORDER BY symbol
</select>
```

> ⚠️ **count 查询不能带 `orderBy`**：PostgreSQL 报 `column must appear in the GROUP BY clause`。
> 规范：**先 count，再 orderBy + selectPage**。

#### 2.3.5 分页

**分页在 Service 层用 `Page<T>` + 分页插件**，XML 里**不写** `LIMIT ... OFFSET ...`。

```java
// ✅ 正确（Service 层）
var pageParam = new Page<StockPoolPO>(query.getPage(), query.getPageSize());
List<StockPoolPO> records = stockPoolMapper.selectPage(pageParam, wrapper).getRecords();
```

> ❌ 反例：XML 里手写 `LIMIT #{limit} OFFSET #{offset}` —— 绕过分页插件，页码深时性能劣化，且 count/list 不一致。

### 2.4 返回类型三分法

| 返回类型 | 用途 | 示例 |
|---|---|---|
| **PO** | 单表完整映射 | `List<StockInfoPO>` |
| **视图行 `XxxRow`** | 联表 / 聚合的结果集（**不是任何单表的映射**）| `List<StockInfoMapper.StockStatRow>` |
| **聚合标量** | `long` / `Integer` / `String` | `long countKline(...)`、`String selectMaxSyncedAt()` |

#### 2.4.1 视图行命名与位置

| 项 | 规范 |
|---|---|
| **命名** | `XxxRow`（**不要**叫 `DTO` / `VO`——它既不是请求也不是视图，是 SQL 结果集）|
| **位置** | **独立成文件** `mapper/row/XxxRow.java` |
| **字段类型** | 与 SQL 列**严格对齐**：金额 `BigDecimal`、日期 `LocalDate`、计数 `Long` |
| **字段名** | 与 SQL 的 `AS` 别名一致（camelCase ↔ snake_case 由 `map-underscore-to-camel-case: true` 自动处理）|

> ⚠️ **接口内部类的坑**：定义成 Mapper 接口的内部类虽然能跑，但：
> 1. 内部类不可被其他 Mapper 复用（同一份定义写两遍，字段变更需同步改两处）；
> 2. `$` 在 MyBatis 的类名解析里容易踩坑；
> 3. 行数多时接口文件被撑爆。
>
> **规范：Row 一律独立成文件。**

> 📌 **命名辨析**：VO 包下的 `XxxRowVO`（如 `BlockTradeRowVO`）是**接口出参**（给前端），属于 VO；
> Mapper 的 `XxxRow` 是**SQL 结果集**（给 Service）。两者概念不同，**不可混用同一个类**。

### 2.5 类型转换在 Mapper 层完成

日期 / 金额的类型转换**应该在 SQL 里做完**，不要把字符串甩给 Service 再解析。

```xml
<!-- ❌ 错误：Mapper 返回 String，Service 再 LocalDate.parse -->
<select id="selectMinKlineDate" resultType="java.lang.String">
    SELECT MIN(date)::text FROM tech_kline_daily WHERE symbol = #{symbol}
</select>

<!-- ✅ 正确：直接映射为日期类型 -->
<select id="selectMinKlineDate" resultType="java.time.LocalDate">
    SELECT MIN(date) FROM tech_kline_daily WHERE symbol = #{symbol}
</select>
```

### 2.6 批量方法约定

| 规则 | 说明 |
|---|---|
| **命名** | `selectXxxByIds` / `selectXxxBatch` / `selectXxxBySymbols` |
| **入参** | `List<T>` + `@Param("ids")`，**必须能处理空集合**（§2.3.3）|
| **返回** | 与入参**可对齐**的视图行列表，Service 侧自行按 key 分组 |
| **禁止** | 在 XML 里 `UNION` 多次单查；禁止 Service 侧循环调用单查（N+1）|

### 2.7 单表查询：Service 侧 wrapper 的写法要求

虽然 wrapper 在 Service 层组装，但**列名必须用 Lambda 引用**（`PO::getXxx`），不能用字符串。

```java
// ✅ 正确：编译期可校验，重构安全
new LambdaQueryWrapper<TechKlinePO>()
        .eq(TechKlinePO::getSymbol, symbol)
        .ge(TechKlinePO::getDate, startDate);

// ❌ 错误：列名写死字符串，拼错不报错
new QueryWrapper<TechKlinePO>().eq("symbol", symbol).ge("date", startDate);
```

> 详见 `Service层规范.md` §3.2。本节只强调：**Lambda 引用要求 PO 字段名与列名保持语义一致**，
> Mapper 返回的 PO 字段一旦改名，Service 侧会**编译期报错**——这是好事，不要用 `@TableField` 掩盖。

### 2.8 写操作

| 规则 | 说明 |
|---|---|
| **单表单条写** | `insert` / `updateById` / `deleteById` |
| **批量写** | XML `<insert>` + `<foreach>`，或 Service 侧 `insertBatch`（需确认 MP 版本支持）|
| **逻辑删除** | 若启用 `@TableLogic`，**删除一律走 `deleteById` / `delete(wrapper)`**，禁止写 SQL `DELETE` |
| **乐观锁** | 若启用 `@Version`，更新必须带版本号，禁止手写 `UPDATE ... SET` 绕过 |
| **禁止** | Mapper 里写 `@Transactional`（事务只在 Service，见 `Service层规范.md` §2.3）|

> 📌 **本项目约定**：当前是**物理删除 + 无乐观锁**（未启用 `@TableLogic` / `@Version`）。
> 若后续引入逻辑删除或乐观锁，需同步更新本节与 `POJO规范.md` §3.6。

---

## 3. Mapper 层「不该做」什么

### 3.1 ❌ 禁止：注解 SQL

```java
// ❌ 错误
@Select("SELECT * FROM tech_kline_daily WHERE symbol = #{symbol}")
List<TechKlinePO> selectBySymbol(@Param("symbol") String symbol);

@Update("UPDATE stock_pools SET name = #{name} WHERE id = #{id}")
int updateName(...);
```

**理由**：SQL 散落在 Java 文件里，无法统一 review、无法复用片段、无法统一分页。

### 3.2 ❌ 禁止：字符串拼接 / `${}`

```xml
<!-- ❌ 错误：SQL 注入 -->
WHERE symbol = '${symbol}'
WHERE table_name = '${tableName}'

<!-- ✅ 正确：预编译绑定 -->
WHERE symbol = #{symbol}
```

动态表名 / 列名必须走**白名单枚举**：

```java
// ✅ 正确：白名单
private static final Set<String> ALLOWED_TABLES = Set.of("tech_kline_daily", "fundamental_daily_basic");
String table = ALLOWED_TABLES.contains(input) ? input : "tech_kline_daily";
```

### 3.3 ❌ 禁止：Service 层裸 JDBC（越权到 Service 的反面）

```java
// ❌ 错误：Service 直接连库
try (Connection conn = dataSource.getConnection();
     Statement stmt = conn.createStatement()) {
    ResultSet rs = stmt.executeQuery("SELECT ... WHERE symbol='" + symbol + "'");
}
```

### 3.4 ❌ 禁止：Mapper 里出现业务判断

```java
// ❌ 错误：Mapper 不知道「默认池不能删」
if (pool.getIsDefault()) throw new BusinessException(400, "默认池不能删除");
```

业务规则一律在 Service；Mapper 只负责「查出来 / 存进去」。

### 3.5 ❌ 禁止：Mapper 返回 VO

```java
// ❌ 错误：Mapper 不认识 VO
List<PoolVO> selectPools();
```

**Mapper 返回 PO 或 Row，VO 由 Service 层的 Converter 产出**（见 `POJO规范.md` §4.3）。

### 3.6 ❌ 禁止：`<foreach>` 里用 `${}`

```xml
<!-- ❌ 错误 -->
<foreach collection="symbols" item="s">${s}</foreach>

<!-- ✅ 正确 -->
<foreach collection="symbols" item="s">#{s}</foreach>
```

### 3.7 ❌ 禁止：Mapper 里做分页 SQL 片段

```xml
<!-- ❌ 错误：绕过分页插件，count/list 不一致 -->
LIMIT #{limit} OFFSET #{offset}
```

### 3.8 ❌ 禁止：Mapper 持有可变静态状态 / 缓存

```java
// ❌ 错误
private static Map<String, Object> cache = new HashMap<>();
```

缓存属于 Service 或 Redis。

---

## 4. 决策流程（写代码时照着走）

```
我要查数据库
  │
  ├─ 单表 + 简单条件？
  │   └─ 是 → Service 里 LambdaQueryWrapper，不写 Mapper 方法
  │
  ├─ 单表 + 分页？
  │   └─ 是 → Service 里 Page<T> + selectPage
  │
  ├─ 单表 + 取前 N？
  │   └─ 是 → Service 里 TopN.query(mapper, wrapper, n)
  │
  ├─ 需要 JOIN / GROUP BY / 多次往返 / CTE？
  │   └─ 是 → 写 XML Mapper
  │       ├─ 返回 PO？→ 可以
  │       ├─ 返回多表拼装结果？→ 定义 XxxRow（独立文件）
  │       └─ 返回单个标量？→ long / Integer / LocalDate
  │
  ├─ 参数是集合？
  │   └─ 是 → XML 内 <choose> 防空集合 + Service 侧前置 return
  │
  └─ count 与 list 都做？
      └─ 是 → 抽 <sql> 片段复用，且 count 不带 orderBy
```

---

## 5. Mapper 方法与 XML 模板

### 5.1 单表（无需自定义方法）

```java
// Mapper 接口：什么都不用加
@Mapper
public interface TechKlineMapper extends BaseMapper<TechKlinePO> {}
```

```java
// Service 层使用
var wrapper = new LambdaQueryWrapper<TechKlinePO>()
        .eq(TechKlinePO::getSymbol, symbol)
        .ge(TechKlinePO::getDate, startDate)
        .orderByDesc(TechKlinePO::getDate);
List<TechKlinePO> rows = TopN.query(techKlineMapper, wrapper, limit);
```

### 5.2 联表 + 视图行

```java
@Mapper
public interface StockInfoMapper extends BaseMapper<StockInfoPO> {

    /** 批量取股票所属自选池（跨表联查） */
    List<PoolMembershipRow> selectPoolMemberships(@Param("symbols") List<String> symbols);
}
```

```xml
<select id="selectPoolMemberships" resultType="com.attribution.market.mapper.row.PoolMembershipRow">
    SELECT m.symbol AS symbol,
           p.id     AS pool_id,
           p.name   AS name,
           p.pool_type AS pool_type
    FROM stock_pool_members m
    JOIN stock_pools p ON p.id = m.pool_id
    WHERE m.symbol IN
    <choose>
        <when test="symbols != null and symbols.size() > 0">
            <foreach collection="symbols" item="symbol" open="(" separator="," close=")">
                #{symbol}
            </foreach>
        </when>
        <otherwise>NULL</otherwise>
    </choose>
      AND (p.is_archived IS NULL OR p.is_archived = false)
    ORDER BY m.symbol, p.id
</select>
```

### 5.3 聚合（GROUP BY）

```java
/** 批量统计各池的成员数（一次查询替代 Service 层逐池 count） */
List<PoolMemberCountRow> selectMemberCounts(@Param("poolIds") List<Integer> poolIds);
```

```xml
<select id="selectMemberCounts" resultType="...row.PoolMemberCountRow">
    SELECT pool_id, COUNT(*) AS member_count
    FROM stock_pool_members
    WHERE pool_id IN
    <foreach collection="poolIds" item="poolId" open="(" separator="," close=")">
        #{poolId}
    </foreach>
    GROUP BY pool_id
</select>
```

### 5.4 CTE 聚合（范本）

```xml
<!-- 一次查询替代 Service 层逐行 5 次查库 -->
<select id="selectStockStats" resultType="...row.StockStatRow">
    WITH kline AS (
        SELECT symbol,
               COUNT(*)        AS record_count,
               MIN(date)       AS kline_start,
               MAX(date)       AS kline_end
        FROM tech_kline_daily
        WHERE symbol IN
        <foreach collection="symbols" item="symbol" open="(" separator="," close=")">
            #{symbol}
        </foreach>
        GROUP BY symbol
    ),
    latest_basic AS (
        SELECT d.symbol, d.close, d.total_mv, d.pe_ttm
        FROM fundamental_daily_basic d
        JOIN (SELECT symbol, MAX(trade_date) AS md
              FROM fundamental_daily_basic
              WHERE symbol IN
              <foreach collection="symbols" item="symbol" open="(" separator="," close=")">
                  #{symbol}
              </foreach>
              GROUP BY symbol) t
          ON t.symbol = d.symbol AND t.md = d.trade_date
    )
    SELECT k.symbol, k.record_count, k.kline_start, k.kline_end,
           b.close AS latest_close, b.total_mv, b.pe_ttm
    FROM kline k
    LEFT JOIN latest_basic b ON b.symbol = k.symbol
</select>
```

### 5.5 聚合标量

```java
/** K 线记录数 */
long countKline(@Param("symbol") String symbol);

/** K 线最早日期 */
LocalDate selectMinKlineDate(@Param("symbol") String symbol);
```

```xml
<select id="countKline" resultType="long">
    SELECT COUNT(*) FROM tech_kline_daily WHERE symbol = #{symbol}
</select>

<select id="selectMinKlineDate" resultType="java.time.LocalDate">
    SELECT MIN(date) FROM tech_kline_daily WHERE symbol = #{symbol}
</select>
```

---

## 6. Code Review 清单

| # | 检查项 | 违规信号 |
|---|---|---|
| 1 | 注解 SQL？ | `@Select` / `@Update` / `@Insert` / `@Delete` |
| 2 | `${}` 拼接？ | `WHERE x = '${x}'` |
| 3 | 手写分页片段？ | XML 里 `LIMIT ... OFFSET ...` |
| 4 | count 与 list 过滤条件一致？ | 两处 `<where>` 内容不同 |
| 5 | count 带 orderBy？ | `selectCount` 的 wrapper 含 `orderBy` |
| 6 | `<foreach>` 防空集合？ | 集合为空时会生成 `IN ()` |
| 7 | 返回类型是 PO / Row / 标量？ | 返回 `XxxVO` |
| 8 | Row 是独立文件？ | 定义在 Mapper 接口内部类里 |
| 9 | 多参数都加了 `@Param`？ | XML 里用 `param1` / `arg0` |
| 10 | 日期/金额类型在 SQL 层完成转换？ | `::text` + Mapper 返回 `String` |
| 11 | Mapper 里有业务 `if` / 抛 `BusinessException`？ | `throw new BusinessException(...)` |
| 12 | Mapper 加了 `@Transactional`？ | 事务注解出现在 Mapper |
| 13 | Mapper 持有静态可变状态？ | `static Map` / `static List` 字段 |
| 14 | 新 Mapper 包已加入 `@MapperScan`？ | `AttributionApp` 的包列表缺新包 |
| 15 | XML 位置正确？ | `src/main/resources/mapper/XxxMapper.xml` |
| 16 | `<select id>` 与方法名一致？ | 改名后漏改 XML |

---

## 7. 新增 Mapper 的检查清单

- [ ] `XxxMapper extends BaseMapper<XxxPO>`，加了 `@Mapper`
- [ ] 新模块的包已加入 `AttributionApp` 的 `@MapperScan`
- [ ] 单表简单查询**没有**新增 Mapper 方法（用 `LambdaQueryWrapper`）
- [ ] 需要 JOIN / GROUP BY / CTE 才写方法，且有配套 XML
- [ ] XML 在 `resources/mapper/XxxMapper.xml`，`namespace` = 接口全限定名
- [ ] `<select id>` 与方法名**完全一致**
- [ ] 多个参数**全部**加了 `@Param`
- [ ] 返回 PO / `XxxRow` / 标量，**不是 VO**
- [ ] `XxxRow` 是**独立文件**（`mapper/row/`），不重复定义
- [ ] 集合参数有 `<choose>` 空集合防护（XML 侧 + Service 侧双保险）
- [ ] count 与 list 共用 `<sql>` 片段，count 不带 orderBy
- [ ] XML 里**没有** `LIMIT/OFFSET`，**没有** `${}`
- [ ] 日期 / 金额类型在 SQL 层转换完成
- [ ] 方法有 Javadoc（`@param` / `@return`）
- [ ] XML 有中文注释说明用途

---

## 8. 技术前提（环境事实，长期有效）

| 项 | 值 | 来源 |
|---|---|---|
| ORM | MyBatis-Plus 3.5.7 | `pom.xml` |
| 数据库 | PostgreSQL | `spring.datasource.url` |
| 基础接口 | `BaseMapper<XxxPO>` | MyBatis-Plus |
| Mapper 扫描 | `@MapperScan` 覆盖 `market` / `concept` / `user` / `auth` 四个包 | `AttributionApp` |
| XML 位置 | `classpath*:/mapper/**/*.xml` | `application.yml` |
| 下划线转驼峰 | `map-underscore-to-camel-case: true` | `application.yml` |
| 分页插件 | `PaginationInnerInterceptor`，`maxLimit = 10000`，`overflow = false` | `MybatisPlusConfig` |
| 攻击防护 | `BlockAttackInnerInterceptor`（阻断全表 update/delete）| `MybatisPlusConfig` |
| 取前 N 行 | `TopN.query(mapper, wrapper, n)` / `TopN.latest(mapper, wrapper)` | `attribution-common/mybatis/TopN.java` |
| 逻辑删除 | 未启用 `@TableLogic`（物理删除）| 各 `entity/` |
| 乐观锁 | 未启用 `@Version` | 各 `entity/` |
| 事务 | `@Transactional(rollbackFor = Exception.class)`，**只在 Service** | `Service层规范.md` §2.3 |

---

## 9. 与其他文档的关系

| 文档 | 管什么 |
|---|---|
| **`Mapper层规范.md`（本文）** | 持久化唯一入口、XML 规范、批量与聚合、Row 定义、分页 |
| `Service层规范.md` | Service 层**该做什么、不该做什么**、事务、跨模块协作；§3.1 禁止 SQL 的规则与本文互为表里 |
| `POJO规范.md` | PO / DTO / VO 定义规范、字段类型、Converter 写法、视图行 `XxxRow` 的定义位置（§3.7）|
| `Controller层规范.md` | HTTP 协议适配；§3.3 明确 Controller 不得注入 Mapper |
| `../审计与整改/` | **历史快照**：某次整改的实测数字，勿作为规范依据 |

> 分工：**「Mapper 怎么写」看本文；「Mapper 里不该有什么」看 `Service层规范.md` §3.1。**

---

> **本文档只写规则，不含任何现状计数。**
> 新增 Mapper / XML 请按 §6（Code Review 清单）与 §7（新增 Mapper 检查清单）自查。
> 改动 Mapper 返回类型时，**必须同步检查 Service 层的消费代码**——
> `String` → `LocalDate` 这类收敛会在编译期暴露，但 `::text` → 原生类型的**文本格式变化**对前端可能是静默的。
