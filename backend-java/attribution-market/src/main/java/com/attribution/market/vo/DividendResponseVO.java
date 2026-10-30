package com.attribution.market.vo;

import java.util.List;

import lombok.Data;

/** 分红送配响应 */
@Data
public class DividendResponseVO {
    private String symbol;
    private List<DividendRowVO> dividends;
}
