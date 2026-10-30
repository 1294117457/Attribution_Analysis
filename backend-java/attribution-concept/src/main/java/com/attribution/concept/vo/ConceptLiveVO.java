package com.attribution.concept.vo;

import lombok.Data;

/** 概念实时视图对象（来自 collector 实时反查） */
@Data
public class ConceptLiveVO {
    private String conceptCode;
    private String name;
    private String source;
    private String reason;
}
