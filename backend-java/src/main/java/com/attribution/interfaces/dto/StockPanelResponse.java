package com.attribution.interfaces.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.util.List;

/**
 * 股票面板分页响应
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class StockPanelResponse {

    /** 分页_*/
    private List<StockPanelRowVO> rows;

    /** 总数 */
    private long total;

    /** 当前_*/
    private int page;

    /** 每页大小 */
    private int size;

    /** 当前查询交易_*/
    private LocalDate tradeDate;
}
