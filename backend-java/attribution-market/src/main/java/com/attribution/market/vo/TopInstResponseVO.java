package com.attribution.market.vo;

import java.util.List;

import lombok.Data;

/** 机构席位响应 */
@Data
public class TopInstResponseVO {
    private String symbol;
    private Integer days;
    private List<TopInstRowVO> details;
}
