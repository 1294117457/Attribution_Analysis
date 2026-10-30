package com.attribution.concept.vo;

import lombok.Data;

/** 概念行情快照 */
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
    private Boolean stale;
    /** 兼容旧字段，恒为空 */
    private String rankLabel;
    private String upDownLabel;
}
