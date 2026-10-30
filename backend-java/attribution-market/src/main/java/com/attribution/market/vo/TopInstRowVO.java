package com.attribution.market.vo;

import java.math.BigDecimal;
import java.time.LocalDate;

import lombok.Data;

/** 机构席位明细 */
@Data
public class TopInstRowVO {
    private LocalDate tradeDate;
    private String exalter;
    private String side;
    private BigDecimal buy;
    private BigDecimal buyRate;
    private BigDecimal sell;
    private BigDecimal sellRate;
    private BigDecimal netBuy;
    private String reason;
}
