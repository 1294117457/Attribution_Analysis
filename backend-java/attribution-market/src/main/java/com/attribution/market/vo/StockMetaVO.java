package com.attribution.market.vo;

import java.util.List;

import lombok.Data;

/** 股票元数据（筛选项枚举值） */
@Data
public class StockMetaVO {
    private List<String> industries;
    private List<String> markets;
    private List<String> exchanges;
}
