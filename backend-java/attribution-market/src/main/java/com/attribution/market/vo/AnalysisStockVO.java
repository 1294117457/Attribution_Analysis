package com.attribution.market.vo;

import lombok.Data;

/** 归因分析中的股票基本信息 */
@Data
public class AnalysisStockVO {
    private String symbol;
    private String name;
    private String industry;
    private String market;
}
