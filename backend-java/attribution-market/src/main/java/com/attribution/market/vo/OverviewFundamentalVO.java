package com.attribution.market.vo;

import java.math.BigDecimal;

import lombok.Data;

/** 总览 - 基本面最新估值 */
@Data
public class OverviewFundamentalVO {
    private BigDecimal latestClose;
    private BigDecimal latestPe;
    private BigDecimal latestPb;
    private BigDecimal latestTotalMv;
    private String latestDate;
}
