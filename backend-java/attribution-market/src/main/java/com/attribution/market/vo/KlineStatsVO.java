package com.attribution.market.vo;

import lombok.Data;

/** K 线统计视图对象 */
@Data
public class KlineStatsVO {
    private String symbol;
    private String name;
    private Long count;
    private Double latestClose;
    private Integer latestVolume;
    private String endDate;
    private String startDate;
}
