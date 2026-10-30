package com.attribution.market.vo;

import java.math.BigDecimal;
import java.time.LocalDate;

import lombok.Data;

/** 分红送配记录 */
@Data
public class DividendRowVO {
    private LocalDate endDate;
    private LocalDate annDate;
    private LocalDate recordDate;
    private LocalDate exDate;
    private LocalDate payDate;
    private String divProc;
    private BigDecimal stkDiv;
    private BigDecimal stkBoRate;
    private BigDecimal stkCoRate;
    private BigDecimal cashDiv;
    private BigDecimal cashDivTax;
}
