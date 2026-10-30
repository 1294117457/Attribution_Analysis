package com.attribution.market.vo;

import java.math.BigDecimal;
import java.time.LocalDate;

import lombok.Data;

/** 每日估值指标（单日） */
@Data
public class ValuationRowVO {
    private LocalDate tradeDate;
    private BigDecimal close;
    private BigDecimal turnoverRate;
    private BigDecimal turnoverRateF;
    private BigDecimal volumeRatio;
    private BigDecimal pe;
    private BigDecimal peTtm;
    private BigDecimal pb;
    private BigDecimal ps;
    private BigDecimal psTtm;
    private BigDecimal dvRatio;
    private BigDecimal dvTtm;
    private BigDecimal totalShare;
    private BigDecimal floatShare;
    private BigDecimal totalMv;
    private BigDecimal circMv;
}
