package com.attribution.market.vo;

import java.time.LocalDate;

import lombok.Data;

/** 停复牌记录 */
@Data
public class SuspendEventVO {
    private LocalDate tradeDate;
    private LocalDate suspendTiming;
    private String suspendType;
}
