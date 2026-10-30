package com.attribution.market.entity;

import java.math.BigDecimal;
import java.time.LocalDate;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

@Data
@TableName("fundamental_income")
public class FinReportPO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    private String symbol;

    @TableField("ann_date")
    private LocalDate annDate;

    @TableField("end_date")
    private LocalDate endDate;

    @TableField("report_type")
    private String reportType;

    @TableField("comp_type")
    private String compType;

    @TableField("basic_eps")
    private BigDecimal basicEps;

    @TableField("diluted_eps")
    private BigDecimal dilutedEps;

    @TableField("total_revenue")
    private BigDecimal totalRevenue;

    private BigDecimal revenue;

    @TableField("operate_profit")
    private BigDecimal operateProfit;

    @TableField("total_profit")
    private BigDecimal totalProfit;

    @TableField("n_income")
    private BigDecimal nIncome;

    @TableField("n_income_attr_p")
    private BigDecimal nIncomeAttrP;

    @TableField("total_assets")
    private BigDecimal totalAssets;

    @TableField("total_liab")
    private BigDecimal totalLiab;

    @TableField("total_hldr_eqy_exc_min_int")
    private BigDecimal totalHldrEqyExcMinInt;

    @TableField("n_cashflow_act")
    private BigDecimal nCashflowAct;

    @TableField("n_cash_flows_fnc_act")
    private BigDecimal nCashFlowsFncAct;

    @TableField("n_cashflow_inv_act")
    private BigDecimal nCashflowInvAct;

    @TableField("data_source")
    private String dataSource;
}
