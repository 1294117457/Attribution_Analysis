package com.attribution.market.vo;

import java.util.List;

import lombok.Data;

/** 大宗交易响应 */
@Data
public class BlockTradeResponseVO {
    private String symbol;
    private Integer days;
    private List<BlockTradeRowVO> trades;
}
