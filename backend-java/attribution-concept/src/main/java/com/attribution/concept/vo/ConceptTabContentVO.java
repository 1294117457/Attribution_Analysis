package com.attribution.concept.vo;

import java.util.List;

import lombok.Data;

/** 概念 Tab 完整内容 */
@Data
public class ConceptTabContentVO {
    private String symbol;
    private String stockName;
    private List<ConceptTabSectionVO> sections;
    private Integer totalCount;
    /** 是否经过实时合并 */
    private Boolean isMerged;
    /** 合并时间（ISO 字符串） */
    private String lastMergedAt;
}
