package com.attribution.domain.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.Id;
import jakarta.persistence.IdClass;
import jakarta.persistence.Index;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.io.Serializable;
import java.time.LocalDateTime;
import java.util.Objects;

@Entity
@Table(
    name = "stock_pool_members",
    indexes = {
        @Index(name = "ix_stock_pool_members_symbol", columnList = "symbol")
    }
)
@IdClass(StockPoolMemberEntity.PoolMemberPK.class)
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class StockPoolMemberEntity {

    @Id
    @Column(name = "pool_id", nullable = false)
    private Long poolId;

    @Id
    @Column(name = "symbol", nullable = false, length = 10)
    private String symbol;

    @Column(name = "memo", length = 255)
    private String memo;

    @Column(name = "sort_order", nullable = false)
    @Builder.Default
    private Integer sortOrder = 0;

    @Column(name = "added_at", nullable = false)
    @Builder.Default
    private LocalDateTime addedAt = LocalDateTime.now();

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "pool_id", insertable = false, updatable = false)
    private StockPoolEntity pool;

    @Getter
    @Setter
    @NoArgsConstructor
    @AllArgsConstructor
    public static class PoolMemberPK implements Serializable {
        private Long poolId;
        private String symbol;

        @Override
        public boolean equals(Object o) {
            if (this == o) return true;
            if (!(o instanceof PoolMemberPK pk)) return false;
            return Objects.equals(poolId, pk.poolId) && Objects.equals(symbol, pk.symbol);
        }

        @Override
        public int hashCode() {
            return Objects.hash(poolId, symbol);
        }
    }
}
