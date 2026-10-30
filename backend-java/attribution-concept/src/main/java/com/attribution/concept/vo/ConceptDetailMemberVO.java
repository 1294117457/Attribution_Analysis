package com.attribution.concept.vo;

import lombok.Data;

/** 概念详情中的成员项 */
@Data
public class ConceptDetailMemberVO {
    private String symbol;
    private String name;
    /** 入选理由 */
    private String reason;
}
