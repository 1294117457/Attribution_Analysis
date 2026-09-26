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

    @Column(name = "symbol", nullable = false, length = 10)
    private String symbol;

    @Column(name = "name", length = 50)
    private String name;

    @Column(name = "date", nullable = false)
    private LocalDate date;

    @Column(name = "open", nullable = false)
    private Double open;

    @Column(name = "high", nullable = false)
    private Double high;

    @Column(name = "low", nullable = false)
    private Double low;

    @Column(name = "close", nullable = false)
    private Double close;

    @Column(name = "volume", nullable = false)
    private Long volume;

    @Column(name = "amount", nullable = false)
    private Double amount;

    @Column(name = "change_pct")
    private Double changePct;

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

    @Column(name = "boll_mid")
    private Double bollMid;

    @Column(name = "boll_up")
    private Double bollUp;

    @Column(name = "boll_dn")
    private Double bollDn;

    @CreatedDate
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @LastModifiedDate
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;
}
