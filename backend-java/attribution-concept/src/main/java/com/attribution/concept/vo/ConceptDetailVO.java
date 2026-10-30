package com.attribution.concept.vo;

import java.util.List;

import lombok.Data;

/** 概念详情（含成员列表） */
@Data
public class ConceptDetailVO extends ConceptVO {
    private List<ConceptDetailMemberVO> members;
}
