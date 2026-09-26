# Python → Java 字段映射规则

> **这是整个重构项目的杠杆文件。** 220 个 Python 文件中，90% 是 `entity + schemas + repository` 模板。一旦这套映射规则定稿，后续的 Entity/Repository 可以批量生成，将原本 3 周的手工编码压缩到 1 周。

## 一、映射总览

### 1.1 Python → Java 类型对照表

| Python 类型 | Java 类型 | JPA 注解 | PostgreSQL 列类型 | 示例 |
|---|---|---|---|---|
| `int` | `Integer` / `Long` | `@Id`, `@GeneratedValue` | `SERIAL` / `BIGSERIAL` | 主键 ID |
| `float` | `Double` | `@Column(precision=..., scale=...)` | `DOUBLE PRECISION` | 价格、成交量 |
| `str` | `String` | `@Column(length=...)` | `VARCHAR(n)` | 股票代码、名称 |
| `bool` | `Boolean` | `@Column(nullable=...)` | `BOOLEAN` | 是否默认、是否归档 |
| `datetime` | `LocalDateTime` | `@Column` | `TIMESTAMP` | 创建时间、更新时间 |
| `date` | `LocalDate` | `@Column` | `DATE` | 交易日期 |
| `dict` (JSON) | `Map<String, Object>` 或 `JsonNode` | `@Column(columnDefinition = "jsonb")` | `JSONB` | params、progress |
| `list` | `List<String>` | `@ElementCollection` | `TEXT[]` 或 JSON | 符号列表 |
| `Enum` | `enum` | `@Enumerated` | `VARCHAR(n)` | 池类型、状态 |

### 1.2 命名规范转换

| Python 风格 | Java 风格 | 说明 |
|---|---|---|
| `snake_case` | `camelCase` | 字段名 Java 标准 |
| `trade_date` | `tradeDate` | 驼峰命名 |
| `is_default` | `isDefault` | Boolean 字段保留 `is` 前缀 |
| `created_at` | `createdAt` | 时间字段 |
| `stock_pools` (table) | `stock_pools` | 表名保持 snake_case（PostgreSQL 习惯） |
| `StockPoolDB` (class) | `StockPoolEntity` | Entity 类名 |  |
| `PoolVO` | `PoolResponse` | DTO 类名 | Response 后缀 |

## 二、Entity 映射模板

### 2.1 基础 Entity 模板

```java
package com.attribution.domain.entity;

import jakarta.persistence.*;
import lombok.*;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import java.time.LocalDateTime;

/**
 * [Entity 描述]
 */
@Entity
@Table(name = "[表名]", indexes = {
    // 索引定义
}, uniqueConstraints = {
    // 唯一约束
})
@EntityListeners(AuditingEntityListener.class)
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class [EntityName] {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // ── 业务字段 ──────────────────────────────────────────────────────────────

    // ── 审计字段 ──────────────────────────────────────────────────────────────

    @CreatedDate
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @LastModifiedDate
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;
}
```

### 2.2 一对多关系模板

```java
// 一的一方
@OneToMany(mappedBy = "[反向引用字段名]", cascade = CascadeType.ALL, orphanRemoval = true)
@Builder.Default
private List<[子实体]> [子实体列表] = new ArrayList<>();

// 多的一方
@ManyToOne(fetch = FetchType.LAZY)
@JoinColumn(name = "[外键列名]", nullable = false)
private [父实体> [反向引用字段];
```

## 三、完整示例：Kline

### 3.1 Python Entity → Java Entity

**Python (domain/kline/entity.py)**:
```python
@dataclass
class Kline(AggregateRoot):
    id: int
    symbol: StockCode          # 值对象
    trade_date: TradeDate      # 值对象
    name: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float
    change_pct: Optional[float] = None
    created_at: Optional[date] = None
    updated_at: Optional[date] = None

    # 17 个技术指标
    ma5: Optional[float] = None
    ma10: Optional[float] = None
    # ... (略)
    boll_dn: Optional[float] = None
```

**Java (TechKlineDailyEntity.java)**:
```java
package com.attribution.domain.entity;

import jakarta.persistence.*;
import lombok.*;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(
    name = "tech_kline_dailys",
    uniqueConstraints = {
        @UniqueConstraint(name = "uq_tech_kline_symbol_date", columnNames = {"symbol", "date"})
    },
    indexes = {
        @Index(name = "ix_tech_kline_symbol_date", columnList = "symbol, date")
    }
)
@EntityListeners(AuditingEntityListener.class)
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class TechKlineDailyEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // ── 业务字段 ──────────────────────────────────────────────────────────────

    @Column(name = "symbol", nullable = false, length = 10)
    private String symbol;  // StockCode 值对象展开为 String

    @Column(name = "name", length = 50)
    private String name;

    @Column(name = "date", nullable = false)
    private LocalDate tradeDate;  // TradeDate 值对象展开为 LocalDate

    @Column(name = "open", nullable = false)
    private Double open;

    @Column(name = "high", nullable = false)
    private Double high;

    @Column(name = "low", nullable = false)
    private Double low;

    @Column(name = "close", nullable = false)
    private Double close;

    @Column(name = "volume", nullable = false)
    private Integer volume;

    @Column(name = "amount", nullable = false)
    private Double amount;

    @Column(name = "change_pct")
    private Double changePct;  // snake_case → camelCase

    // ── 技术指标（17 列）─────────────────────────────────────────────────────

    @Column(name = "ma5")
    private Double ma5;

    @Column(name = "ma10")
    private Double ma10;

    @Column(name = "ma20")
    private Double ma20;

    @Column(name = "ma60")
    private Double ma60;

    @Column(name = "ema12")
    private Double ema12;

    @Column(name = "ema26")
    private Double ema26;

    @Column(name = "macd_dif")
    private Double macdDif;

    @Column(name = "macd_dea")
    private Double macdDea;

    @Column(name = "macd_bar")
    private Double macdBar;

    @Column(name = "rsi6")
    private Double rsi6;

    @Column(name = "rsi12")
    private Double rsi12;

    @Column(name = "rsi24")
    private Double rsi24;

    @Column(name = "kdj_k")
    private Double kdjK;

    @Column(name = "kdj_d")
    private Double kdjD;

    @Column(name = "kdj_j")
    private Double kdjJ;

    @Column(name = "boll_up")
    private Double bollUp;

    @Column(name = "boll_mid")
    private Double bollMid;

    @Column(name = "boll_dn")
    private Double bollDn;

    // ── 审计字段 ──────────────────────────────────────────────────────────────

    @CreatedDate
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @LastModifiedDate
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;
}
```

## 四、完整示例：StockPool

### 4.1 Python Model → Java Entity

**Python (infrastructure/database/models/pool.py)**:
```python
class StockPoolDB(Base, TimestampMixin):
    __tablename__ = "stock_pools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pool_type: Mapped[str] = mapped_column(String(32), nullable=False, default="custom", index=True)
    color: Mapped[str | None] = mapped_column(String(16), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    owner_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    share_token: Mapped[str | None] = mapped_column(String(64), nullable=True)

    members: Mapped[list["StockPoolMemberDB"]] = relationship(...)
    operations: Mapped[list["PoolOperationDB"]] = relationship(...)


class StockPoolMemberDB(Base):
    __tablename__ = "stock_pool_members"

    pool_id: Mapped[int] = mapped_column(Integer, ForeignKey("stock_pools.id", ondelete="CASCADE"), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(10), primary_key=True, index=True)
    memo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    added_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.now)

    pool: Mapped["StockPoolDB"] = relationship(back_populates="members")


class PoolOperationDB(Base):
    __tablename__ = "pool_operations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pool_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("stock_pools.id", ondelete="SET NULL"), nullable=True, index=True)
    operation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True)
    params: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    result_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    progress: Mapped[dict] = mapped_column(JSON, nullable=False, default=lambda: {...})
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.now)
```

**Java (StockPoolEntity.java)**:
```java
package com.attribution.domain.entity;

import jakarta.persistence.*;
import lombok.*;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(
    name = "stock_pools",
    indexes = {
        @Index(name = "ix_stock_pools_updated_at", columnList = "updated_at")
    }
)
@EntityListeners(AuditingEntityListener.class)
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class StockPoolEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "name", nullable = false, length = 64)
    private String name;

    @Column(name = "description", length = 255)
    private String description;

    @Column(name = "pool_type", nullable = false, length = 32)
    private String poolType;  // Enum: watchlist, custom

    @Column(name = "color", length = 16)
    private String color;

    @Column(name = "icon", length = 32)
    private String icon;

    @Column(name = "sort_order", nullable = false)
    @Builder.Default
    private Integer sortOrder = 0;

    @Column(name = "is_default", nullable = false)
    @Builder.Default
    private Boolean isDefault = false;

    @Column(name = "is_archived", nullable = false)
    @Builder.Default
    private Boolean isArchived = false;

    @Column(name = "owner_id")
    private Long ownerId;

    @Column(name = "share_token", length = 64)
    private String shareToken;

    // ── 关联 ─────────────────────────────────────────────────────────────────

    @OneToMany(mappedBy = "pool", cascade = CascadeType.ALL, orphanRemoval = true)
    @Builder.Default
    private List<StockPoolMemberEntity> members = new ArrayList<>();

    @OneToMany(mappedBy = "pool")
    @Builder.Default
    private List<PoolOperationEntity> operations = new ArrayList<>();

    // ── 审计字段 ──────────────────────────────────────────────────────────────

    @CreatedDate
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @LastModifiedDate
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;
}
```

**Java (StockPoolMemberEntity.java)**:
```java
package com.attribution.domain.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.LocalDateTime;

@Entity
@Table(name = "stock_pool_members")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class StockPoolMemberEntity {

    @EmbeddedId
    private StockPoolMemberId id;

    @Column(name = "memo", length = 255)
    private String memo;

    @Column(name = "sort_order", nullable = false)
    @Builder.Default
    private Integer sortOrder = 0;

    @Column(name = "added_at", nullable = false)
    private LocalDateTime addedAt;

    @ManyToOne(fetch = FetchType.LAZY)
    @MapsId("poolId")
    @JoinColumn(name = "pool_id", nullable = false)
    private StockPoolEntity pool;
}

@Embeddable
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class StockPoolMemberId implements Serializable {
    @Column(name = "pool_id")
    private Long poolId;

    @Column(name = "symbol", length = 10)
    private String symbol;
}
```

**Java (PoolOperationEntity.java)**:
```java
package com.attribution.domain.entity;

import jakarta.persistence.*;
import lombok.*;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

@Entity
@Table(
    name = "pool_operations",
    indexes = {
        @Index(name = "ix_pool_operations_type_status", columnList = "operation_type, status"),
        @Index(name = "ix_pool_operations_created_at", columnList = "created_at"),
        @Index(name = "ix_pool_operations_pool_time", columnList = "pool_id, created_at")
    }
)
@EntityListeners(AuditingEntityListener.class)
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class PoolOperationEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "pool_id")
    private Long poolId;

    @Column(name = "operation_type", nullable = false, length = 32)
    private String operationType;

    @Column(name = "status", nullable = false, length = 16)
    @Builder.Default
    private String status = "pending";

    @Column(name = "params", columnDefinition = "jsonb", nullable = false)
    @Convert(converter = MapToJsonConverter.class)
    @Builder.Default
    private Map<String, Object> params = new HashMap<>();

    @Column(name = "result_summary", columnDefinition = "jsonb")
    @Convert(converter = MapToJsonConverter.class)
    private Map<String, Object> resultSummary;

    @Column(name = "progress", columnDefinition = "jsonb", nullable = false)
    @Convert(converter = MapToJsonConverter.class)
    @Builder.Default
    private Map<String, Object> progress = new HashMap<>();

    @Column(name = "error_message", columnDefinition = "TEXT")
    private String errorMessage;

    @Column(name = "started_at")
    private LocalDateTime startedAt;

    @Column(name = "finished_at")
    private LocalDateTime finishedAt;

    @CreatedDate
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "pool_id", insertable = false, updatable = false)
    private StockPoolEntity pool;
}
```

## 五、完整示例：概念板块

**Python (concept/entity.py + models/concept.py)**:

Python `domain/concept/entity.py` 有 `Concept` 和 `ConceptMember`。

**Java (ConceptEntity.java + ConceptMemberEntity.java)**:

```java
@Entity
@Table(name = "concepts")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ConceptEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "concept_code", nullable = false, unique = true, length = 20)
    private String conceptCode;

    @Column(name = "concept_name", nullable = false, length = 100)
    private String conceptName;

    @Column(name = "market", length = 20)
    private String market;

    @Column(name = "source", length = 20)
    private String source;

    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @OneToMany(mappedBy = "concept", cascade = CascadeType.ALL, orphanRemoval = true)
    @Builder.Default
    private List<ConceptMemberEntity> members = new ArrayList<>();
}

@Entity
@Table(name = "concept_members")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ConceptMemberEntity {

    @EmbeddedId
    private ConceptMemberId id;

    @ManyToOne(fetch = FetchType.LAZY)
    @MapsId("conceptId")
    @JoinColumn(name = "concept_id", nullable = false)
    private ConceptEntity concept;
}

@Embeddable
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ConceptMemberId implements Serializable {
    @Column(name = "concept_id")
    private Long conceptId;

    @Column(name = "symbol", length = 10)
    private String symbol;
}
```

## 六、批量生成策略

### 6.1 生成顺序

```
1. 枚举类 (Enum)           → PoolTypeEnum, OperationStatus
2. 值对象 (Value Object)  → StockCode, TradeDate
3. Embeddable ID          → StockPoolMemberId, ...
4. 实体类 (Entity)        → TechKlineDailyEntity, StockPoolEntity, ...
5. Repository 接口       → JpaRepository
6. RepositoryImpl        → Spring Data JPA (可能不需要手动写)
7. DTO 类                 → Request/Response
8. Service 类             → 应用服务
9. Controller 类          → REST API
```

### 6.2 实体类自动生成检查清单

每个实体类必须包含：

- [ ] `@Entity` 注解
- [ ] `@Table(name = "...", indexes = {...}, uniqueConstraints = {...})`
- [ ] `@Id` + `@GeneratedValue(strategy = GenerationType.IDENTITY)`
- [ ] 所有字段的 `@Column(name = "...", length = ..., nullable = ...)`
- [ ] 所有 `@OneToMany` / `@ManyToOne` 关系
- [ ] `@EntityListeners(AuditingEntityListener.class)`
- [ ] `@CreatedDate` / `@LastModifiedDate` 审计字段
- [ ] Lombok 注解 (`@Getter`, `@Setter`, `@Builder`, `@NoArgsConstructor`, `@AllArgsConstructor`)
- [ ] 构造方法（无参 + 全参）

## 七、JSONB 字段处理

### 7.1 PostgreSQL JSONB → Java Map 转换器

```java
@Converter(autoApply = true)
public class MapToJsonConverter implements AttributeConverter<Map<String, Object>, JsonNode> {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Override
    public JsonNode convertToDatabaseColumn(Map<String, Object> attribute) {
        if (attribute == null) {
            return NullNode.getInstance();
        }
        return objectMapper.valueToTree(attribute);
    }

    @Override
    public Map<String, Object> convertToEntityAttribute(JsonNode dbData) {
        if (dbData == null || dbData.isNull()) {
            return new HashMap<>();
        }
        return objectMapper.convertValue(dbData, new TypeReference<Map<String, Object>>() {});
    }
}
```

## 八、所有领域模型清单

| 领域 | Entity | 表名 | 字段数 | 复杂度 |
|---|---|---|---|---|
| kline | TechKlineDailyEntity | tech_kline_dailys | 28 | 高 |
| stock_pool | StockPoolEntity, StockPoolMemberEntity, PoolOperationEntity | stock_pools, stock_pool_members, pool_operations | 22 | 中 |
| stock_info | StockInfoEntity, IndustryEntity, MarketEntity | stock_infos, industries, markets | 25 | 中 |
| fin_report | FinReportEntity | fin_reports | 20 | 中 |
| fin_daily_basic | FinDailyBasicEntity | fin_daily_basics | 15 | 低 |
| concept | ConceptEntity, ConceptMemberEntity | concepts, concept_members | 12 | 中 |
| cap_margin | CapMarginEntity | cap_margins | 12 | 低 |
| cap_margin_detail | CapMarginDetailEntity | cap_margin_details | 10 | 低 |
| cap_top_list | CapTopListEntity | cap_top_lists | 10 | 低 |
| cap_top_inst | CapTopInstEntity | cap_top_insts | 10 | 低 |
| cap_block_trade | CapBlockTradeEntity | cap_block_trades | 10 | 低 |
| cap_moneyflow | CapMoneyflowEntity | cap_moneyflows | 12 | 低 |
| cap_holder_num | CapHolderNumEntity | cap_holder_nums | 8 | 低 |
| fin_top10_holders | FinTop10HoldersEntity | fin_top10_holders | 10 | 低 |
| fin_top10_float | FinTop10FloatHolderEntity | fin_top10_float_holders | 10 | 低 |
| base_adj_factor | BaseAdjFactorEntity | base_adj_factors | 6 | 低 |
| base_dividend | BaseDividendEntity | base_dividends | 10 | 低 |
| base_suspend | BaseSuspendEntity | base_suspends | 8 | 低 |
| base_name_change | BaseNameChangeEntity | base_name_changes | 8 | 低 |
| mkt_calendar | MktCalendarEntity | mkt_calendars | 6 | 低 |
| mkt_market_daily | MktMarketDailyEntity | mkt_market_dailys | 12 | 低 |
| mkt_sector_daily | MktSectorDailyEntity | mkt_sector_dailys | 10 | 低 |
| mkt_index_member | MktIndexMemberEntity | mkt_index_members | 8 | 低 |
