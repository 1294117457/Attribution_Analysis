package com.attribution.market.vo;

import java.util.List;

import lombok.Data;

/** 股票归因分析响应 */
@Data
public class StockAnalysisVO {
    private AnalysisStockVO stock;
    private TechnicalSummaryVO summary;
    private List<KlineVO> klines;
    private List<PoolMembershipVO> pools;
}
