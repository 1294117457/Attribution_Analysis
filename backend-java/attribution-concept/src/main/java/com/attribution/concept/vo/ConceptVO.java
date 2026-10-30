package com.attribution.concept.vo;

import java.time.LocalDateTime;

import lombok.Data;

/** 概念视图对象 */
@Data
public class ConceptVO {
    private Integer conceptId;
    private String indexCode;
    private String name;
    private String source;
    private String conceptType;
    private Integer stockCount;
    private String description;
    private Boolean isActive;
    private LocalDateTime lastSyncedAt;
    private LocalDateTime firstSeenAt;
}
