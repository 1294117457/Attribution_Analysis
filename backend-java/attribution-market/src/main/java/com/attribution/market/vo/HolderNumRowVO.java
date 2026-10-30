package com.attribution.market.vo;

import java.math.BigDecimal;
import java.time.LocalDate;

import lombok.Data;

/** 股东户数历史 */
@Data
public class HolderNumRowVO {
    private LocalDate endDate;
    private LocalDate annDate;
    private Integer holderNum;
    private BigDecimal holderNums;
}
