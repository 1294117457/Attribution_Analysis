package com.attribution.market.vo;

import java.util.List;

import lombok.Data;

/** 曾用名变更响应 */
@Data
public class NameChangeResponseVO {
    private String symbol;
    private List<NameChangeVO> history;
}
