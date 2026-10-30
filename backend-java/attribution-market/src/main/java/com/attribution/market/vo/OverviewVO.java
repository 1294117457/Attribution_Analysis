package com.attribution.market.vo;

import lombok.Data;

/** 看板总览响应 */
@Data
public class OverviewVO {
    private String symbol;
    private OverviewStockVO stock;
    private OverviewTechVO tech;
    private OverviewFundamentalVO fundamental;
    private OverviewCapitalVO capital;
    private OverviewNewsVO news;
}
