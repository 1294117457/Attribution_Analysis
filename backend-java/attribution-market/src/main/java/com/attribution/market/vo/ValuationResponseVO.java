package com.attribution.market.vo;

import java.util.List;

import lombok.Data;

/** 每日估值响应 */
@Data
public class ValuationResponseVO {
    private String symbol;
    private Integer days;
    private List<ValuationRowVO> valuation;
}
