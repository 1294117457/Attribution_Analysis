package com.attribution.market.vo;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

import lombok.Data;

/**
 * 股票面板列表项视图对象。
 *
 * <p>对应前端 {@code StockListItem}（stock-info/api.ts）。
 */
@Data
public class StockPanelVO {
    private String symbol;
    private String tsCode;
    private String name;
    private String area;
    private String industry;
    private String market;
    private String exchange;
    /** 上市日期 YYYYMMDD */
    private String listDate;
    private String listStatus;
    private String isHs;
    private String actName;
    private String actEntType;
    private Long totalShares;
    /** K 线记录数 */
    private Integer recordCount;
    private String klineStart;
    private String klineEnd;
    private BigDecimal latestClose;
    private BigDecimal totalMv;
    private BigDecimal peTtm;
    private Double profitMargin;
    /** 所属自选池（withPools=true 时填充） */
    private List<PoolMembershipVO> pools;
    /** 所属概念（withConcepts=true 时填充） */
    private List<ConceptMainVO> concepts;
    /** 概念总数超出主概念位数的部分 */
    private Integer conceptsOverflow;
}
