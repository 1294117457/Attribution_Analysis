package com.attribution.interfaces.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.util.List;

/**
 * 概念详情 - 包含该概念下的成份股分组和板块行_ */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ConceptDetailVO {

    private String code;
    private String name;
    private String source;

    /** 板块近期行情 */
    private List<SectorDailyVO> recentDailies;

    /** 当前成员列表 */
    private List<ConceptMemberVO> members;

    /** 成员数量 */
    private int memberCount;
}
