package com.attribution.market.vo;

import java.util.List;

import lombok.Data;

/** 数据看板 K 线响应 */
@Data
public class TechKlineVO {
    private String symbol;
    private List<MarketKlineVO> klines;
}
