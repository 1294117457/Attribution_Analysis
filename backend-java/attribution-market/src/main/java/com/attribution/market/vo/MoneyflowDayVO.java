package com.attribution.market.vo;

import java.math.BigDecimal;
import java.time.LocalDate;

import lombok.Data;

/** 资金流向（单日） */
@Data
public class MoneyflowDayVO {
    private LocalDate tradeDate;
    private BigDecimal buySmAmount;
    private BigDecimal sellSmAmount;
    private BigDecimal buyMdAmount;
    private BigDecimal sellMdAmount;
    private BigDecimal buyLgAmount;
    private BigDecimal sellLgAmount;
    private BigDecimal buyElgAmount;
    private BigDecimal sellElgAmount;
    private BigDecimal netMfAmount;
    private BigDecimal netMfVol;
}
