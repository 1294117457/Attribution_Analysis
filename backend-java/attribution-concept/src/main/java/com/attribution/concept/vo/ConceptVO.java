package com.attribution.concept.vo;

import java.time.OffsetDateTime;

import lombok.Data;

@Data
public class ConceptVO {
    private Integer conceptId;
    private String indexCode;
    private String name;
    private String source;
    private String conceptType;
    private String description;
    private Integer stockCount;
    private Boolean isActive;
    /** 最近同步时间（timestamptz） */
    private OffsetDateTime lastSyncedAt;
    /** 首次发现时间（timestamptz） */
    private OffsetDateTime firstSeenAt;
}
