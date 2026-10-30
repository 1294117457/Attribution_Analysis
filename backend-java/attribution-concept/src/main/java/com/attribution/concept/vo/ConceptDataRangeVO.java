package com.attribution.concept.vo;

import lombok.Data;

/** 概念 K 线数据区间 */
@Data
public class ConceptDataRangeVO {
    private String start;
    private String end;
    private Integer barsCount;
}
