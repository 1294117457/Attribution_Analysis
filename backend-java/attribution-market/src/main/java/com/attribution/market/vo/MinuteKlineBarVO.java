package com.attribution.market.vo;

import java.math.BigDecimal;

import lombok.Data;

/** 分钟 K 线单根 */
@Data
public class MinuteKlineBarVO {
    private String datetime;
    private String interval;
    private BigDecimal open;
    private BigDecimal high;
    private BigDecimal low;
    private BigDecimal close;
    private BigDecimal volume;
    private BigDecimal amount;
}
