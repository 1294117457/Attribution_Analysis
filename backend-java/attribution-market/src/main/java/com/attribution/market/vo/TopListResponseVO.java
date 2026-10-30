package com.attribution.market.vo;

import java.util.List;

import lombok.Data;

/** 龙虎榜响应 */
@Data
public class TopListResponseVO {
    private String symbol;
    private Integer days;
    private List<TopListRowVO> lists;
}
