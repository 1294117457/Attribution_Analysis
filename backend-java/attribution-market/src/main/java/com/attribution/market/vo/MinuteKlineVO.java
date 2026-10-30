package com.attribution.market.vo;

import java.math.BigDecimal;
import java.util.List;

import lombok.Data;

/** 分钟 K 线响应 */
@Data
public class MinuteKlineVO {
    private String symbol;
    private String interval;
    private List<MinuteKlineBarVO> bars;
    private Boolean cached;
    private String fetchedAt;
}
