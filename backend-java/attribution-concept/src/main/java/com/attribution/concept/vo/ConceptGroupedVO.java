package com.attribution.concept.vo;

import java.util.List;

import lombok.Data;

/** 概念分组（详情抽屉「概念」Tab 用） */
@Data
public class ConceptGroupedVO {
    private Integer conceptId;
    private String indexCode;
    private String name;
    private String source;
    private String conceptType;
    private String description;
    /** 入选理由 */
    private String reason;
    /** 板块行情快照 */
    private ConceptSnapshotVO snapshot;
    /** mergeLive=true 时携带 */
    private Boolean isRealtime;
    /** mergeLive=true 时携带 */
    private String conceptCode;
}
