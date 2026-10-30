# POJO 分层规范（DTO / BO / VO / PO）

> 适用范围：`backend-java` 全部 Maven 模块
> 核心原则：**用「谁的字段」判断，用「跨了几层」判断。不看字段数量。**
> 同层文档：`Controller层规范.md`（协议适配）、`Service层规范.md`（业务编排）、`Mapper层规范.md`（持久化）

---

## 1. 四个概念的边界

| 概念 | 归属层 | 生命周期 | 命名 | 包路径 |
|---|---|---|---|---|
| **PO** | Mapper ↔ DB | 请求内 | `XxxPO` | `entity/` |
| **DTO** | Controller → Service | 一次调用 | `XxxRequest` / `XxxQuery` | `dto/` |
| **BO** | Service 内部 | 一次业务操作 | `XxxBO` | `bo/` |
| **VO** | Service → 前端 | 一次响应 | `XxxVO` | `vo/` |

```
Controller ──DTO──▶ Service ──BO(可选)──▶ Mapper ──PO──▶ DB
▲                 │
└──────VO─────────┘
```

**BO 是 Service 的私有实现细节**，不出现在接口签名、不跨模块、不序列化给前端。

---

## 2. 决策标准

### 2.1 入参（Controller → Service）

```
收到一个入参对象
  ├─ 结构是「外部定义的」（透传 Python collector / 第三方）？ → 保持 Map，不定义 DTO
  ├─ 本模块自己定义
  │   ├─ ≤2 个标量字段            → 不定义 DTO，直接用方法参数
  │   ├─ ≥3 个字段 / 含集合嵌套    → 定义 DTO
  │   ├─ 同一对象被多个接口接收    → 必须定义 DTO
  │   └─ PATCH 部分更新            → 必须定义 DTO，字段全用包装类型
  └─ 成对语义（如 oldPassword/newPassword） → 定义 DTO，不用两个平行 String
```

### 2.2 出参（Service → 前端）

```
要返回给前端的数据
  ├─ 自由结构透传                        → 保持 Map
  ├─ 需脱敏 / 改字段名 / 加计算字段      → 定义 VO
  ├─ 列表元素需多表拼装                  → 定义 VO（拼装结果本就不是表映射）
  ├─ 分页                                → PageResult<XxxVO>
  └─ 与 PO 字段完全一致且无敏感字段        → 可直接返 PO，但推荐转 VO
```

### 2.3 BO 的判定（必须同时满足 ≥2 条）

1. 跨 Service 调用传递
2. 不是任何单张表的映射（多来源聚合）
3. 承载业务规则计算
4. 有独立生命周期和状态

> **无真实需求不建 BO**，避免空壳类。

### 2.4 可以保留 Map 的场景

| 场景 | 理由 |
|---|---|
| 数据结构由外部系统定义（Python collector / 第三方）| 跨语言契约，Java 定义 DTO 会造成两语言强耦合：Python 改字段 → Java 编译失败 |
| 前端契约本身是动态 key（`Record<string, Xxx>`）| 动态 key 无法用固定字段的 DTO 表达；**但 value 仍应是 `XxxVO`** |
| Util 的内部计算中间态 | 非接口契约，对外由 Converter 转 VO |

---

## 3. 定义规范

### 3.1 DTO

```java
package com.attribution.auth.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

import lombok.Data;

@Data
public class LoginRequest {
    @NotBlank(message = "邮箱不能为空")
    @Email(message = "邮箱格式不正确")
    private String email;

    @NotBlank(message = "密码不能为空")
    @Size(min = 6, max = 64, message = "密码长度需在 6-64 位之间")
    private String password;

    @NotBlank(message = "验证码不能为空")
    private String captchaId;

    @NotBlank(message = "验证码不能为空")
    private String captchaCode;

    /** user-agent 由后端从 HttpServletRequest 取，不接受前端传 */
    private String userAgent;

    /** 同上 */
    private String clientIp;
}
```

| 项 | 规范 |
|---|---|
| 注解 | `@Data` + `jakarta.validation.constraints.*` |
| 命名 | 入参 `XxxRequest`；查询条件 `XxxQuery` |
| 字段类型 | PATCH 场景**必须用包装类型**（`Integer`/`Boolean`），否则无法区分「没传」与「传了 0/false」|
| 客户端 IP / UA | **不入 DTO**，Controller 从 `HttpServletRequest` 取，防伪造 |
| Lombok | 只用 `@Data`，**不要** `@Builder`+`@NoArgsConstructor` 组合（Jackson 需无参构造）|

### 3.2 常用校验注解

```java
@NotBlank   // 字符串非空白
@NotNull    // 对象/数字非空
@NotEmpty   // 集合非空
@Size(min=, max=)   // 长度/集合大小
@Email
@Pattern(regexp = "^[0-9]{6}$", message = "验证码为 6 位数字")
@Min(1) @Max(200)  // pageSize 等数值范围
@DecimalMin("0.0") @DecimalMax("999999999999.99")
```

### 3.3 校验的触发方式

**必须 `@RequestBody` + `@Valid`**（`@RequestBody` 才触发 Bean Validation）：

```java
@PostMapping("/login")
public ApiResponse<TokenVO> login(@Valid @RequestBody LoginRequest request, HttpServletRequest httpRequest) {
    return ApiResponse.ok(authService.login(request, httpRequest.getRemoteAddr()));
}
```

| 写法 | 行为 |
|---|---|
| `@RequestBody Map<String,Object> body` | **无任何校验**，字段名靠手写字符串 |
| `@Valid @RequestBody LoginRequest req` | 触发校验，失败抛 `MethodArgumentNotValidException` |
| `@RequestParam String email` | 触发校验，但逐个参数，不适合多字段 |

`GlobalExceptionHandler` 处理校验失败，返回 **422 + 全部字段错误**（`joining("; ")`），前端拦截器直接弹提示，**前端零改动**。

### 3.4 校验的分层

| 层 | 职责 | 例子 |
|---|---|---|
| **DTO `@Valid`** | **格式**校验 | 长度、格式、范围、必填 |
| **Service** | **业务规则**校验 | 邮箱已注册、密码不匹配、状态冲突 |

> 原则：能用注解表达的不用 `if`，能用 `if` 表达的不用查库。

### 3.5 VO

```java
package com.attribution.auth.vo;

import java.time.LocalDateTime;
import java.util.List;

import lombok.Data;

@Data
public class UserVO {
    private Integer id;
    private String email;
    private String nickname;
    private String avatarUrl;
    private Boolean isActive;
    private Boolean isVerified;
    private List<RoleBriefVO> roles;
    private List<String> roleCodes;
    private List<String> permissions;
    private LocalDateTime createdAt;
    private LocalDateTime lastLoginAt;
}
```

| 项 | 规范 |
|---|---|
| **禁止**包含 | `passwordHash` 等敏感字段、`isSystem` 等内部字段 |
| 字段名 | camelCase，Jackson `SNAKE_CASE` 自动转 snake_case 给前端 |
| 可空性 | 用包装类型，前端要能区分「没值」和「0」|
| 嵌套 | 用 `XxxBriefVO`（精简）/ `XxxDetailVO`（完整）|

### 3.6 PO

```java
package com.attribution.market.entity;

@Data
@TableName("tech_kline_daily")
public class TechKlinePO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    private String symbol;
    private LocalDate date;
    private BigDecimal open;      // 金额用 BigDecimal，不用 double
    private BigDecimal high;
    private BigDecimal low;
    private BigDecimal close;
    private Integer volume;
    private BigDecimal amount;

    @TableField("change_pct")
    private BigDecimal changePct;
}
```

| 项 | 规范 |
|---|---|
| 注解 | `@Data` + `@TableName` + `@TableId` + `@TableField`（列名不匹配才加）|
| 类型 | 金额 `BigDecimal`；时间 `LocalDate` / `LocalDateTime` |
| **禁止** | 业务计算方法、继承、**出现在 Controller 方法签名上** |

### 3.7 视图行 `XxxRow`

联表 / 聚合的结果集叫 `XxxRow`（不是 DTO / VO）——它是**SQL 结果集**，不是接口契约。

| 项 | 规范 |
|---|---|
| 命名 | `XxxRow` |
| 位置 | `mapper/row/XxxRow.java`（**独立文件**，不要定义成 Mapper 接口内部类）|
| 字段类型 | 与 SQL 列严格对齐：金额 `BigDecimal`、日期 `LocalDate`、计数 `Long` |
| 可见性 | 只在 Mapper → Service 之间流动，**不直接返回给前端** |

> 📌 完整规则见 `Mapper层规范.md` §2.4。

---

## 4. 转换规范

### 4.1 方案选择

| 方案 | 结论 |
|---|---|
| **手写静态工厂** | ✅ **本项目首选**（字段 3~15 个，成本可接受，行为完全可控）|
| **MapStruct** | 映射点 > 30 处时再引入 |
| `BeanUtils.copyProperties` | ❌ 禁止。字段名不匹配**静默失败**，类型转换不严 |
| 构造器 / Builder 注入 | ✅ 组合对象（BO）首选 |

### 4.2 Converter 实现

放在 `com.attribution.<module>.converter`，独立包（一个 VO 常有多个来源，放 VO 内会让 VO 承担转换职责）。

```java
package com.attribution.auth.converter;

import java.util.List;

import com.attribution.auth.entity.UserPO;
import com.attribution.auth.vo.UserVO;

public final class UserConverter {

    private UserConverter() {
    }   // 工具类禁止实例化

    public static UserVO toVO(UserPO po) {
        if (po == null) return null;
        UserVO vo = new UserVO();
        vo.setId(po.getId());
        vo.setEmail(po.getEmail());
        vo.setNickname(po.getNickname());
        vo.setAvatarUrl(po.getAvatarUrl());
        vo.setIsActive(po.getIsActive());
        vo.setIsVerified(po.getIsVerified());
        vo.setCreatedAt(po.getCreatedAt());
        vo.setLastLoginAt(po.getLastLoginAt());
        // passwordHash 故意不拷贝 —— VO 里没有这个字段
        return vo;
    }

    public static List<UserVO> toVOList(List<UserPO> pos) {
        return pos == null ? List.of() : pos.stream().map(UserConverter::toVO).toList();
    }
}
```

### 4.3 转换的放置位置

**转换发生在 Service 层**——Mapper 只取数不认识 VO，Controller 只管协议不认识 PO。

```java
PO = mapper.selectOne(...);          // Mapper 层
VO = UserConverter.toVO(po);         // Service 层
return ApiResponse.ok(vo);           // Controller 层
```

### 4.3.1 Converter 需要 ObjectMapper 时：传参，不要 new

部分 PO 的字段以 JSON 文本存库（如操作记录的 `params` / `progress` / `result_summary`），
反序列化需要 `ObjectMapper`。**必须使用 Spring 容器管理的实例**——
它带全局配置（`SNAKE_CASE` 命名策略、日期格式、未知属性策略、`JavaTimeModule`）。

```java
// ❌ 禁止：裸实例不带全局配置，序列化结果与全局约定不一致
private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

// ✅ 正确：Converter 保持静态工具类，ObjectMapper 由 Service 注入后透传
public static PoolOperationVO toVO(PoolOperationPO po, ObjectMapper mapper) { ... }
```

| 项 | 规范 |
|---|---|
| Converter 形态 | **保持静态工具类**（`final` + 私有构造 + 静态方法），不要为了拿 ObjectMapper 改成 Spring Bean |
| ObjectMapper 来源 | Service 层用 `@RequiredArgsConstructor` / 构造器注入 Spring 管理的 Bean |
| 传参方式 | 作为**方法参数**传入 Converter |
| 序列化与反序列化 | 必须用**同一个实例**，否则写入格式与读取格式可能不一致 |

> 📌 详见 `../横切技术规范/基础设施规范.md` §5.5（外部调用与序列化）。

### 4.4 DTO → PO：不直接映射

DTO 不直接转 PO，中间必须有业务加工。

```java
// ❌ 禁止
UserPO po = new UserPO();
BeanUtils.copyProperties(req, po);

// ✅ 显式映射 + 业务加工
UserPO po = new UserPO();
po.setEmail(req.getEmail().toLowerCase().trim());              // 归一化
po.setPasswordHash(passwordEncoder.encode(req.getPassword()));  // 加密
po.setNickname(resolveNickname(req));                           // 业务默认
po.setIsActive(true);
userMapper.insert(po);
return UserConverter.toVO(po);
```

### 4.5 BO 的转换

BO 涉及多源聚合，用显式构造或 Builder：

```java
StockAnalysisBO bo = new StockAnalysisBO();
bo.setStock(stockMapper.selectOne(...));
bo.setKlines(klineMapper.selectList(...));
bo.setSummary(IndicatorUtil.summarize(...));
bo.setPools(poolService.findPoolsBySymbol(symbol));  // 跨模块调 Service，不调 Mapper
```

---

## 5. 完整示例：创建自选池

**① DTO** `attribution-user/dto/PoolCreateRequest.java`

```java
@Data
public class PoolCreateRequest {
    @NotBlank(message = "池名称不能为空")
    @Size(max = 64, message = "池名称最长 64 字符")
    private String name;

    @Size(max = 255, message = "描述最长 255 字符")
    private String description;

    private String poolType = "custom";
    private String color;
    private String icon;
}
```

**② Controller**——只做绑定 + 校验 + 调 Service

```java
@PostMapping("/pools")
public ApiResponse<PoolVO> create(@Valid @RequestBody PoolCreateRequest request) {
    return ApiResponse.created(poolService.create(request));
}
```

**③ Service 接口**——用 DTO/VO 表达契约

```java
public interface PoolService {
    PoolVO create(PoolCreateRequest request);
    PageResult<PoolVO> list(PoolListQuery query);
    void update(Integer poolId, PoolUpdateRequest request);
}
```

**④ Service 实现**——业务编排 + PO↔DTO/VO 转换

```java
@Override
public PoolVO create(PoolCreateRequest request) {
    StockPoolPO po = new StockPoolPO();
    po.setName(request.getName().trim());
    po.setDescription(request.getDescription());
    po.setPoolType(request.getPoolType());
    po.setIsArchived(false);
    po.setIsDefault(false);
    stockPoolMapper.insert(po);
    return PoolConverter.toVO(po, 0);
}
```

**⑤ VO / ⑥ Converter**——见 §3.5 / §4.2

---

## 6. 速查表

| 问题 | 答案 |
|---|---|
| 1~2 个标量字段，要定义 DTO 吗？ | **不要**，用方法参数 |
| ≥3 个字段？ | **要**，`XxxRequest` |
| PATCH 部分更新？ | **要**，且必须用包装类型 |
| 同一入参被多个接口用？ | **必须** |
| 结构是外部定义的？ | **不要**，保持 Map |
| 出参需脱敏/改名/加计算字段？ | **要**，`XxxVO` |
| 出参 = PO 原样？ | 可直返 PO，推荐转 VO |
| 需要跨 Service 传聚合对象？ | 定义 **BO**（需同时满足 ≥2 条判定）|
| PO 能直接给前端吗？ | **不能**，必须转 VO |
| Mapper 返回什么？ | **PO** 或视图行 `XxxRow`（见 `Mapper层规范.md`）|
| 转换放哪层？ | **Service 层** |
| 转换用什么？ | 手写静态工厂（字段少）/ MapStruct（字段多）|
| Service 能写 SQL 吗？ | **不能**，一律下沉 Mapper |
| 校验注解放哪？ | **DTO**（格式）+ Service（业务规则）|
| 分页出参？ | `PageResult<XxxVO>`，禁止裸 Map、自定义字段名 |

---

## 7. 三个务实提醒

1. **VO 与前端联动**：Jackson `SNAKE_CASE` 会自动转字段名，改 VO 字段名时前端手写 TS **不会报错**，会静默拿到 `undefined`。改 VO 字段名时必须同步改前端 TS，或引入 OpenAPI 生成。

2. **不要为「统一」消灭所有 Map**：透传 Python collector 的结构时，保持 Map 是对的（见 §2.4）。

3. **BO 先别建**：无真实跨 Service 聚合传递场景时，无需求不建。

---

## 8. 技术前提（环境事实，长期有效）

| 项 | 值 | 来源 |
|---|---|---|
| Lombok | `@Data`（DTO / VO / PO）| `pom.xml` |
| 校验框架 | Jakarta Bean Validation（`jakarta.validation.constraints.*`）| `pom.xml` |
| JSON 命名策略 | `SNAKE_CASE` | `spring.jackson.property-naming-strategy` |
| 日期时间序列化 | `LocalDate` / `LocalDateTime`，不转时间戳 | `application.yml` |
| 统一响应 | `{code, message, data}` | `ApiResponse` |
| 分页出参 | `PageResult<T>` | `attribution-common/response/PageResult.java` |
| PO 表名映射 | `@TableName` / `@TableId` / `@TableField` | MyBatis-Plus |
| 包路径约定 | `dto/` `vo/` `bo/` `entity/` `converter/`（各模块内）| 各模块目录结构 |
| 视图行路径 | `mapper/row/XxxRow.java` | `Mapper层规范.md` §2.4 |

---

## 9. 与其他文档的关系

| 文档 | 管什么 |
|---|---|
| **`POJO规范.md`（本文）** | DTO / PO / VO / BO / Row 的**定义规范**：字段类型、校验注解、Converter 写法 |
| `Controller层规范.md` | Controller 层**路径、参数绑定、校验、响应封装**、豁免场景 |
| `Service层规范.md` | Service 层**该做什么、不该做什么**、事务、跨模块协作 |
| `Mapper层规范.md` | **持久化唯一入口**：XML 写法、批量与聚合、视图行定义、分页 |
| `../审计与整改/` | **历史快照**：某次整改的实测数字，勿作为规范依据 |

> 四份文档的分工：**「用什么形状传递数据」看本文；「哪层负责什么」看三份分层规范。**

---

> **本文档只写规则，不含任何现状计数。**
> 改动 VO / DTO 字段名时，**必须同步前端 TS**（Jackson `SNAKE_CASE` 会让字段名改动对前端静默失效）。
