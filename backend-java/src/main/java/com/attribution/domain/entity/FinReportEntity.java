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
    name = "fin_reports",
    uniqueConstraints = {
        @UniqueConstraint(name = "uq_fin_reports_uk", columnNames = {"symbol", "end_date"})
    },
    indexes = {
        @Index(name = "ix_fin_reports_symbol_end", columnList = "symbol, end_date")
    }
)
@EntityListeners(AuditingEntityListener.class)
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class FinReportEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "symbol", nullable = false, length = 10)
    private String symbol;

    @Column(name = "ann_date")
    private LocalDate annDate;

    @Column(name = "end_date", nullable = false)
    private LocalDate endDate;

    @Column(name = "report_type", length = 16)
    private String reportType;

    @Column(name = "comp_type", length = 16)
    private String compType;

    @Column(name = "basic_eps")
    private Double basicEps;

    @Column(name = "diluted_eps")
    private Double dilutedEps;

    @Column(name = "total_revenue")
    private Double totalRevenue;

    @Column(name = "revenue")
    private Double revenue;

    @Column(name = "operate_profit")
    private Double operateProfit;

    @Column(name = "total_profit")
    private Double totalProfit;

    @Column(name = "n_income")
    private Double nIncome;

    @Column(name = "n_income_attr_p")
    private Double nIncomeAttrP;

    @Column(name = "total_assets")
    private Double totalAssets;

    @Column(name = "total_liab")
    private Double totalLiab;

    @Column(name = "total_hldr_eqy_exc_min_int")
    private Double totalHldrEqyExcMinInt;

    @Column(name = "n_cashflow_act")
    private Double nCashflowAct;

    @Column(name = "n_cash_flows_fnc_act")
    private Double nCashFlowsFncAct;

    @Column(name = "n_cashflow_inv_act")
    private Double nCashflowInvAct;

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
