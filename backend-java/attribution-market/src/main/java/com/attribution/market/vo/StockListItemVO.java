package com.attribution.market.vo;

import java.util.List;

import lombok.Data;

/** 看板股票列表项（精简） */
@Data
public class StockListItemVO {
    private String symbol;
    private String name;
    private String industry;
    private String market;
    private String exchange;
    private String listStatus;
}
