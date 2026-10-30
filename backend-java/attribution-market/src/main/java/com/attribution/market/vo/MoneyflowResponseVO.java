package com.attribution.market.vo;

import java.util.List;

import lombok.Data;

/** 资金流向响应 */
@Data
public class MoneyflowResponseVO {
    private String symbol;
    private Integer days;
    private List<MoneyflowDayVO> flows;
}
