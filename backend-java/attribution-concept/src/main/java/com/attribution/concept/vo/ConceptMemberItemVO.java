package com.attribution.concept.vo;

import java.math.BigDecimal;
import java.util.List;

import lombok.Data;

/** 概念成员列表项 */
@Data
public class ConceptMemberItemVO {
    private String symbol;
    private String name;
    private String industry;
    private String market;
    private BigDecimal latestClose;
    private BigDecimal totalMv;
    private BigDecimal peTtm;
    private Double pctChange;
    /** up / down / flat */
    private String color;
    /** 所属自选池（withPools=true 时填充） */
    private List<PoolMembershipVO> pools;
}
