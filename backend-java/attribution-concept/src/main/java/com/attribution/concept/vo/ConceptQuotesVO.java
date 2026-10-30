package com.attribution.concept.vo;

import java.util.List;

import lombok.Data;

/** 概念实时行情批量响应：index_code → snapshot */
@Data
public class ConceptQuotesVO {
    private List<ConceptSnapshotVO> quotes;
}
