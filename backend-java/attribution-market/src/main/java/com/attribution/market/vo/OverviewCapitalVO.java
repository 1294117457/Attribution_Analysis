package com.attribution.market.vo;

import lombok.Data;

/** 总览 - 资金面数据统计 */
@Data
public class OverviewCapitalVO {
    private String moneyflowLatestDate;
    private Long moneyflowCount;
    private String marginLatestDate;
    private Long marginCount;
    private Long topListCount;
    private Long holderCount;
}
