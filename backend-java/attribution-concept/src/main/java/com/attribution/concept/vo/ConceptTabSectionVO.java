package com.attribution.concept.vo;

import java.util.List;

import lombok.Data;

/** 概念 Tab 单个分组区块 */
@Data
public class ConceptTabSectionVO {
    private String type;
    private String typeLabel;
    private List<ConceptGroupedVO> concepts;
}
