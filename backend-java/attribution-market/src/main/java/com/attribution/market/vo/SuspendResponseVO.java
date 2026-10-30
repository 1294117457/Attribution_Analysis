package com.attribution.market.vo;

import java.util.List;

import lombok.Data;

/** 停复牌记录响应 */
@Data
public class SuspendResponseVO {
    private String symbol;
    private List<SuspendEventVO> events;
}
