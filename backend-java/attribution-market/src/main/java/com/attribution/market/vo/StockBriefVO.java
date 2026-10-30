package com.attribution.market.vo;

import lombok.Data;

/**
 * 股票基础信息摘要。
 *
 * <p>属于 market 领域，供其他模块（如 attribution-user 的自选池）复用，
 * 避免各模块重复定义同义 VO。
 */
@Data
public class StockBriefVO {
    private String symbol;
    private String name;
    private String industry;
    private String market;
    private String exchange;
}
