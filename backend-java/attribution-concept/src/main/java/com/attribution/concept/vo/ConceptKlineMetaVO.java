package com.attribution.concept.vo;

import lombok.Data;

/** 概念 K 线元信息 */
@Data
public class ConceptKlineMetaVO {
    private Integer conceptId;
    private String indexCode;
    private String name;
    private String conceptType;
    private String conceptTypeLabel;
    private Integer stockCount;
    private String description;
    private String source;
}
