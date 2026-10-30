package com.attribution.market.vo;

import java.math.BigDecimal;
import java.time.LocalDate;

import lombok.Data;

/** 财务报表摘要 */
@Data
public class FinReportRowVO {
    private LocalDate endDate;
    private LocalDate annDate;
    private String reportType;
    private BigDecimal basicEps;
    private BigDecimal dilutedEps;
    private BigDecimal totalRevenue;
    private BigDecimal revenue;
    private BigDecimal operateProfit;
    private BigDecimal totalProfit;
    private BigDecimal nIncome;
    private BigDecimal nIncomeAttrP;
    /** 净利率（%），由 revenue / n_income 计算 */
    private Double netMargin;
}
