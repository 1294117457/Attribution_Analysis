package com.attribution.interfaces.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.util.List;

/**
 * 财务报告 + 估_+ 资金面聚_- 用于股票详情抽屉的财_Tab
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class StockFinanceSnapshotVO {

    private String symbol;

    /** 最新财务报_*/
    private LocalDate reportEndDate;
    private Double basicEps;
    private Double dilutedEps;
    private Double totalRevenue;
    private Double revenue;
    private Double operateProfit;
    private Double totalProfit;
    private Double nIncome;
    private Double nIncomeAttrP;
    private Double totalAssets;
    private Double totalLiab;
    private Double totalHldrEqyExcMinInt;
    private Double nCashflowAct;
    private Double nCashFlowsFncAct;
    private Double nCashflowInvAct;

    /** 股东户数 */
    private Integer latestHolderNum;
    private LocalDate latestHolderDate;

    /** 前十大股_*/
    private List<TopHolderVO> topHolders;

    /** 分红 */
    private List<DividendVO> dividends;
}
