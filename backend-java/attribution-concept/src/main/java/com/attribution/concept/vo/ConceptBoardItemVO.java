package com.attribution.concept.vo;

import lombok.Data;

/** 概念大盘列表项 */
@Data
public class ConceptBoardItemVO {
    private Integer conceptId;
    private String indexCode;
    private String name;
    private String source;
    private String conceptType;
    private String conceptTypeLabel;
    private Integer stockCount;
    private String description;
    private Double price;
    private Double prevClose;
    private Double change;
    private Double pctChange;
    /** up / down / flat */
    private String color;
    private String tradeTime;
    private String capturedAt;
    private Boolean stale;
}
