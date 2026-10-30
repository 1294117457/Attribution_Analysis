package com.attribution.market.vo;

import lombok.Data;

/** 概念板块行情快照 */
@Data
public class ConceptSnapshotVO {
    private String indexCode;
    private String conceptName;
    private Double price;
    private Double prevClose;
    private Double change;
    private Double pctChange;
    /** up / down / flat */
    private String color;
    private String tradeTime;
    private String capturedAt;
    /** true=行情源不可用，显示的是最近一条日 K 收盘 */
    private Boolean stale;
}
