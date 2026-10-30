package com.attribution.market.vo;

import java.math.BigDecimal;
import java.time.LocalDate;

import lombok.Data;

/** 十大流通股东明细 */
@Data
public class Top10FloatRowVO {
    private LocalDate endDate;
    private LocalDate annDate;
    private String holderName;
    private BigDecimal holdAmount;
    private BigDecimal holdRatio;
    private BigDecimal holdChange;
    private String holderType;
}
