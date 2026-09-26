package com.attribution.domain.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EntityListeners;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
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
    name = "cap_top_lists",
    uniqueConstraints = {
        @UniqueConstraint(name = "uq_cap_top_lists_uk", columnNames = {"trade_date", "symbol", "reason"})
    },
    indexes = {
        @Index(name = "ix_cap_top_lists_date", columnList = "trade_date")
    }
)
@EntityListeners(AuditingEntityListener.class)
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class CapTopListEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "trade_date", nullable = false)
    private LocalDate tradeDate;

    @Column(name = "symbol", nullable = false, length = 10)
    private String symbol;

    @Column(name = "name", length = 50)
    private String name;

    @Column(name = "close")
    private Double close;

    @Column(name = "pct_change")
    private Double pctChange;

    @Column(name = "turnover_rate")
    private Double turnoverRate;

    @Column(name = "amount")
    private Double amount;

    @Column(name = "l_sell")
    private Double lSell;

    @Column(name = "l_buy")
    private Double lBuy;

    @Column(name = "l_amount")
    private Double lAmount;

    @Column(name = "net_amount")
    private Double netAmount;

    @Column(name = "net_rate")
    private Double netRate;

    @Column(name = "amount_rate")
    private Double amountRate;

    @Column(name = "float_values")
    private Double floatValues;

    @Column(name = "reason", length = 256)
    private String reason;

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
