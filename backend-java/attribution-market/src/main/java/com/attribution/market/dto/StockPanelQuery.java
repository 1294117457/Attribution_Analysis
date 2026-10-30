package com.attribution.market.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;

import lombok.Data;

/**
 * 股票面板列表查询条件。
 *
 * <p>原实现为 13 个位置参数的可读性灾难，此处收敛为一个查询对象。
 */
@Data
public class StockPanelQuery {
    /** 关键字：代码 / 名称 / ts_code 模糊匹配 */
    private String keyword;

    private String industry;

    private String market;

    private String exchange;

    /** 沪深港通标记 N/H/S */
    private String isHs;

    /** 上市状态 L/D/P/UN */
    private String listStatus;

    /** true=只保留非 ST，false=只看 ST，null=不限 */
    private Boolean excludeSt;

    /** 总市值下限（万元） */
    private Double minTotalMv;

    /** 按概念板块过滤 */
    private Integer conceptId;

    @Min(value = 1, message = "页码需大于 0")
    private int page = 1;

    @Min(value = 1, message = "每页条数需大于 0")
    @Max(value = 500, message = "每页条数最多 500")
    private int pageSize = 20;

    /** 是否附带所属自选池 */
    private boolean withPools = false;

    /** 是否附带所属概念 */
    private boolean withConcepts = false;
}
