package com.attribution.concept.vo;

import lombok.Data;

/** 概念简略视图对象（by-symbol 反查） */
@Data
public class ConceptBriefVO {
    private Integer conceptId;
    private String name;
    private String source;
    private String conceptType;
}
