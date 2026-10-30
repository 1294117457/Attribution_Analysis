package com.attribution.market.vo;

import java.time.LocalDate;

import lombok.Data;

/** 停复牌记录 */
@Data
public class SuspendEventVO {
    private LocalDate tradeDate;

    /** 停复牌状态代码（S=停牌 / R=复牌），非日期 */
    private String suspendTiming;

    private String suspendType;
}
