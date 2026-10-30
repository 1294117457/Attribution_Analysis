package com.attribution.market.vo;

import java.math.BigDecimal;
import java.time.LocalDate;

import lombok.Data;

/** 十大股东明细 */
@Data
public class Top10HolderRowVO {
    private LocalDate endDate;
    private LocalDate annDate;
    private String holderName;
    private BigDecimal holdAmount;
    private BigDecimal holdRatio;
    private BigDecimal holdFloatRatio;
    private BigDecimal holdChange;
    private String holderType;
}
