package com.attribution.market.vo;

import lombok.Data;

/** 总览 - 新闻数据可用性 */
@Data
public class OverviewNewsVO {
    private Boolean available = false;
    private String message;
}
