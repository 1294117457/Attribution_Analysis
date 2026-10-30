package com.attribution.market.vo;

import java.util.List;

import lombok.Data;

/** 十大流通股东响应 */
@Data
public class Top10FloatResponseVO {
    private String symbol;
    private List<Top10FloatRowVO> holders;
}
