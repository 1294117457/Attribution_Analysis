package com.attribution.market.vo;

import java.math.BigDecimal;
import java.time.LocalDate;

import lombok.Data;

/** 大宗交易明细 */
@Data
public class BlockTradeRowVO {
    private LocalDate tradeDate;
    private String name;
    private BigDecimal price;
    private BigDecimal vol;
    private BigDecimal amount;
    private String buyer;
    private String seller;
}
