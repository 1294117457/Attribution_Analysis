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
    name = "fin_daily_basics",
    uniqueConstraints = {
        @UniqueConstraint(name = "uq_fin_daily_basics_uk", columnNames = {"symbol", "trade_date"})
    },
    indexes = {
        @Index(name = "ix_fin_daily_basics_date", columnList = "trade_date")
    }
)
@EntityListeners(AuditingEntityListener.class)
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class FinDailyBasicEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "symbol", nullable = false, length = 10)
    private String symbol;

    @Column(name = "trade_date", nullable = false)
    private LocalDate tradeDate;

    @Column(name = "close")
    private Double close;

    @Column(name = "turnover_rate")
    private Double turnoverRate;

    @Column(name = "turnover_rate_f")
    private Double turnoverRateF;

    @Column(name = "volume_ratio")
    private Double volumeRatio;

    @Column(name = "pe")
    private Double pe;

    @Column(name = "pe_ttm")
    private Double peTtm;

    @Column(name = "pb")
    private Double pb;

    @Column(name = "ps")
    private Double ps;

    @Column(name = "ps_ttm")
    private Double psTtm;

    @Column(name = "dv_ratio")
    private Double dvRatio;

    @Column(name = "dv_ttm")
    private Double dvTtm;

    @Column(name = "total_share")
    private Double totalShare;

    @Column(name = "float_share")
    private Double floatShare;

    @Column(name = "free_share")
    private Double freeShare;

    @Column(name = "total_mv")
    private Double totalMv;

    @Column(name = "circ_mv")
    private Double circMv;

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
