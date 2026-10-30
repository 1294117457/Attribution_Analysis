package com.attribution.concept.vo;

import lombok.Data;

/** 概念分时单点 */
@Data
public class ConceptMinuteVO {
    private String indexCode;
    private String conceptName;
    private Double price;
    private Double preClose;
    private Double change;
    private Double changePct;
    private String tradeTime;
    private String capturedAt;
    private Boolean stale;
    private Boolean cached;
    private String fetchedAt;
}
