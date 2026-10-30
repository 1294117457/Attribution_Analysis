package com.attribution.market.vo;

import lombok.Data;

/** 主概念视图对象（在简略视图基础上增加业务排序位次） */
@Data
public class ConceptMainVO {
    private Integer conceptId;
    private String name;
    private String source;
    private String conceptType;
    /** 1=最优先（行业概念），越大越靠后 */
    private Integer displayOrder;
    /** 板块行情快照，无数据时为 null */
    private ConceptSnapshotVO snapshot;
}
