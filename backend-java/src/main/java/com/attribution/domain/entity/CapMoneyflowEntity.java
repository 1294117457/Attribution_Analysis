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
    name = "cap_moneyflows",
    uniqueConstraints = {
        @UniqueConstraint(name = "uq_cap_moneyflow_symbol_date", columnNames = {"symbol", "trade_date"})
    },
    indexes = {
        @Index(name = "ix_cap_moneyflow_date", columnList = "trade_date")
    }
)
@EntityListeners(AuditingEntityListener.class)
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class CapMoneyflowEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "symbol", nullable = false, length = 10)
    private String symbol;

    @Column(name = "trade_date", nullable = false)
    private LocalDate tradeDate;

    @Column(name = "buy_sm_vol")
    private Double buySmVol;

    @Column(name = "buy_sm_amount")
    private Double buySmAmount;

    @Column(name = "sell_sm_vol")
    private Double sellSmVol;

    @Column(name = "sell_sm_amount")
    private Double sellSmAmount;

    @Column(name = "buy_md_vol")
    private Double buyMdVol;

    @Column(name = "buy_md_amount")
    private Double buyMdAmount;

    @Column(name = "sell_md_vol")
    private Double sellMdVol;

    @Column(name = "sell_md_amount")
    private Double sellMdAmount;

    @Column(name = "buy_lg_vol")
    private Double buyLgVol;

    @Column(name = "buy_lg_amount")
    private Double buyLgAmount;

    @Column(name = "sell_lg_vol")
    private Double sellLgVol;

    @Column(name = "sell_lg_amount")
    private Double sellLgAmount;

    @Column(name = "buy_elg_vol")
    private Double buyElgVol;

    @Column(name = "buy_elg_amount")
    private Double buyElgAmount;

    @Column(name = "sell_elg_vol")
    private Double sellElgVol;

    @Column(name = "sell_elg_amount")
    private Double sellElgAmount;

    @Column(name = "net_mf_vol")
    private Double netMfVol;

    @Column(name = "net_mf_amount")
    private Double netMfAmount;

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
