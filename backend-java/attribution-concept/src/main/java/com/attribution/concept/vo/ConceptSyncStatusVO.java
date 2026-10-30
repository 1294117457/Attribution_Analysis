package com.attribution.concept.vo;

import lombok.Data;

/** 概念同步状态 */
@Data
public class ConceptSyncStatusVO {
    private Long activeConcepts;
    private String lastSyncedAt;
}
