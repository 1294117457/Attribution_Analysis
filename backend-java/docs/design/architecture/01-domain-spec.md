# domain 层规范

> domain 是核心，**不依赖任何外部**。可以脱离 Spring 容器单测。

## 1. 包结构

```
com.attribution.domain/
├── entity/         实体
├── vo/             域内值对象（DomainVO，无 ID、按值相等）
├── repository/     仓储接口（仅接口，不放实现）
└── service/        领域服务
```

> ⚠️ domain 层**不允许**依赖 `interface/dto/`（详见 §3.2 / §4.3）。

## 2. Entity 规范

### 必须

- 有唯一标识字段（`id`）
- 用 JPA 注解（`@Entity` / `@Table`）

### 放进 entity 的逻辑

- 单字段校验（`if (price < 0) throw ...`）
- 状态机迁移（`status: PENDING → RUNNING → SUCCESS`）
- 单实体的不变量校验

### 禁止放进 entity

- 跨多实体的校验（→ `DomainService`）
- IO 操作（→ `AppService`）
- 调外部 SDK（→ `AppService`）

### 示例

```java
@Entity
public class StockPoolEntity {

    public void addMember(StockCode code, String memo) {
        if (this.memberCount() >= MAX_MEMBERS) {
            throw new PoolFullException(this.id);
        }
        if (this.contains(code)) {
            throw new DuplicateMemberException(this.id, code);
        }
        this.members.add(new PoolMemberEntity(this.id, code, memo));
    }
}
```

## 3. VO 规范

### 3.1 何时用

- 无唯一标识
- 用值描述业务概念（`TradeDate`、`PoolType`、`OperationStatus`）
- 域内纯计算结果

### 必须

- 不可变（`final` 字段 + 无 setter，或用 record）
- 自带校验逻辑（构造时校验）
- 提供静态工厂方法（`of` / `from`）

### 禁止

- ❌ 继承 `interface/dto/*VO` 或反之
- ❌ 在 domain VO 上加 `@JsonProperty` / `@Schema` 等序列化注解
- ❌ 在 domain VO 上加 Lombok `@Builder` / `@Data`（保持不可变语义）

### 示例

```java
public record TradeDate(LocalDate date) {

    public TradeDate {
        Objects.requireNonNull(date);
        if (date.isBefore(LocalDate.of(1990, 1, 1))) {
            throw new IllegalArgumentException("日期过早");
        }
    }

    public static TradeDate of(LocalDate d)        { return new TradeDate(d); }
    public static TradeDate today()                  { return new TradeDate(LocalDate.now()); }
}
```

### 3.2 DomainVO vs DTO VO（边界）

| 类型 | 位置 | 特征 | 例 |
|------|------|------|----|
| **DomainVO** | `domain/vo/` | 无 ID、按值相等、构造时校验、不可变 | `TradeDate` / `PoolType` / `OperationStatus` / `StockCode` |
| **DTO VO** | `interface/dto/{module}/` | 可有 ID、带关联字段、HTTP 响应定制 | `PoolVO` / `KlineVO` / `StockDetailVO` |

**判定口诀**：

```
这个类型是给谁用的？
│
├── 域内计算（多 entity / VO 之间）   → domain/vo/   （DomainVO）
│
└── 直接给 HTTP 响应（前端要看的）     → interface/dto/  （DTO VO）
```

### 3.3 跨层引用规则

```
domain/vo  ←─ domain/entity  ✅
domain/vo  ←─ domain/service ✅
domain/vo  ←─ application/service ✅

domain/vo  ←─ interface/dto/{module}  ❌（DTO 不能继承域 VO）
domain/vo  ←─ infrastructure/*        ❌
```

> ❌ **DTO 引用 domain VO 做基类**：会让 DTO 行为耦合域逻辑，未来切换序列化协议（如 Protobuf）会很难。

## 4. Repository 规范

### 接口命名

| 操作 | 方法名 |
|------|--------|
| 查单个 | `findById` / `findByXxx` |
| 查列表 | `findAllByXxx` / `findByXxx` |
| 存在性 | `existsByXxx` |
| 统计 | `countByXxx` |
| 写 | `save` / `saveAll` |
| 删 | `deleteById` / `deleteByXxx` |

复杂查询：优先 `Specification` 或 `@Query`。

### 禁止

- 仓储接口放实现（实现在 `infrastructure/persistence/`）
- 在仓储实现里写业务逻辑
- **返回 entity 给 application 层以外**（Controller 不能直接用 entity）
- ❌ **返回 DTO**（详见 §4.3）

### 4.3 Repository 不能返回 DTO（铁律）

> ❌ **错误**：`List<StockPanelRowVO> queryPanel(StockPanelQuery query);`  
> ✅ **正确**：`List<StockPanelRowEntity> queryPanel(StockPanelQuery query);`（返回 entity）  
> ✅ 然后由 `interface.controller` 装配成 `StockPanelResponse`。

**为什么**：
- Repository 是**持久化契约**，返回值应该是 entity（或基本类型、ID）。
- 一旦返回 DTO，Repository 就被"对外格式"绑定，**无法跨端复用**（如未来 GraphQL / RPC 也要复用 Repository）。
- DTO 在装配层（controller 最后一公里）做，DTO 才能根据不同接口协议灵活调整。

### 跨层引用规则

```
domain/repository  ←─ domain/service            ✅
domain/repository  ←─ application/service       ✅
domain/repository  ←─ infrastructure/persistence 实现 ✅

domain/repository  ←─ interface/dto             ❌
domain/repository  返回 interface/dto/*VO        ❌
```

## 5. DomainService 规范

### 何时抽

- 跨 ≥ 2 个 entity 的校验
- 跨 ≥ 2 个 entity 的计算

### 必须

- 只依赖 domain（entity / DomainVO / repository 接口）

### 禁止

- `@Transactional` / `@Cacheable`
- 注入 `HttpClient` / `RestTemplate` / `WebClient`
- 直接持久化（只读 repository 可以）
- ❌ 注入或返回 `interface/dto/*VO`

### 示例

```java
@Service
public class PoolMembershipDomainService {

    private final StockPoolRepository poolRepo;
    private final StockRepository stockRepo;

    public void validateMembership(StockCode code) {
        if (!stockRepo.existsByCode(code)) {
            throw new StockNotFoundException(code);
        }
        if (poolRepo.countAllPoolsContaining(code) > MAX_POOLS_PER_STOCK) {
            throw new StockInTooManyPoolsException(code);
        }
    }
}
```

## 6. 跨层依赖总结

```
domain/
  ↑ ↑
  │ └─── application/service/        （依赖 domain 接口）
  │
  │ └─── infrastructure/persistence/  （实现 domain.repository）
  │
  │ × interface/dto/                 （DTO 不进 domain）
  │ × infrastructure/adapter/         （domain 不感知外部）
```

## 7. 变更记录

| 版本  | 日期       | 变更人 | 变更内容 |
| ----- | ---------- | ------ | -------- |
| v0.1  | 2026-09-25 | -      | 初稿 |
| v0.2  | 2026-09-25 | -      | 新增 DomainVO 与 DTO VO 的边界（§3.2 / §3.3）；新增 Repository 不能返回 DTO 铁律（§4.3）；新增跨层依赖总结（§6） |
