package com.attribution.market.vo;

import java.math.BigDecimal;
import java.time.LocalDate;

import lombok.Data;

/** 复权因子 */
@Data
public class AdjFactorVO {
    private LocalDate tradeDate;
    private BigDecimal adjFactor;
}
