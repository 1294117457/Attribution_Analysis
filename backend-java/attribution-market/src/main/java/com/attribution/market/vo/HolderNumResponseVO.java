package com.attribution.market.vo;

import java.util.List;

import lombok.Data;

/** 股东户数响应 */
@Data
public class HolderNumResponseVO {
    private String symbol;
    private List<HolderNumRowVO> history;
}
