package com.attribution.domain.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EntityListeners;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(
    name = "cap_block_trades",
    indexes = {
        @Index(name = "ix_cap_block_trades_symbol_date", columnList = "symbol, trade_date"),
        @Index(name = "ix_cap_block_trades_date", columnList = "trade_date")
    }
)
@EntityListeners(AuditingEntityListener.class)
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class CapBlockTradeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "trade_date", nullable = false)
    private LocalDate tradeDate;

    @Column(name = "symbol", nullable = false, length = 10)
    private String symbol;

    @Column(name = "name", length = 50)
    private String name;

    @Column(name = "price")
    private Double price;

    @Column(name = "vol")
    private Double vol;

    @Column(name = "amount")
    private Double amount;

    @Column(name = "buyer", length = 128)
    private String buyer;

    @Column(name = "seller", length = 128)
    private String seller;

    @Column(name = "data_source", nullable = false, length = 16)
    @Builder.Default
    private String dataSource = "tushare";

    @CreatedDate
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @LastModifiedDate
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;
}
