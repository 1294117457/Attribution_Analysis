package com.attribution.market.vo;

import java.math.BigDecimal;
import java.time.LocalDate;

import lombok.Data;

/** 龙虎榜明细 */
@Data
public class TopListRowVO {
    private LocalDate tradeDate;
    private String name;
    private BigDecimal close;
    private BigDecimal pctChange;
    private BigDecimal turnoverRate;
    private BigDecimal amount;
    private BigDecimal lBuy;
    private BigDecimal lSell;
    private BigDecimal lAmount;
    private BigDecimal netAmount;
    private BigDecimal netRate;
    private BigDecimal amountRate;
    private BigDecimal floatValues;
    private String reason;
}
