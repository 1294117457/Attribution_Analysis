package com.attribution.market.vo;

import java.util.List;

import lombok.Data;

/** 融资融券响应 */
@Data
public class MarginResponseVO {
    private String symbol;
    private Integer days;
    private List<MarginDayVO> details;
}
