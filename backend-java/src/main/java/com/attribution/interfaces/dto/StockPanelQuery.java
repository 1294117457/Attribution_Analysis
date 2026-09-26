package com.attribution.interfaces.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;

/**
 * 面板查询参数（与前端 stock-info/api.ts StockQueryParams 1:1 对齐）
 *
 * 字段命名使用 camelCase；前端发的 snake_case 由 Controller 层 @RequestParam 显式映射。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class StockPanelQuery {

    /** 页号（从 1 开始）*/
    @Builder.Default
    private int page = 1;

    /** 每页大小 */
    @Builder.Default
    private int size = 20;

    /** 关键字（前端字段 q）*/
    private String keyword;

    /** 行业过滤 */
    private String industry;

    /** 市场（主板/科创板/创业板/北交所）*/
    private String market;

    /** 交易所（SSE/SZSE/BSE）*/
    private String exchange;

    /** 沪深港通（N/H/S）*/
    private String isHs;

    /** 上市状态（L/D/P/UN）*/
    private String listStatus;

    /** 是否排除 ST（true=排除, false=仅 ST, null=不限）*/
    private Boolean excludeSt;

    /** 最小总市值（万元）*/
    private Double minTotalMv;

    /** 板块代码过滤 (概念 / 行业) */
    private String sectorCode;

    /** 板块类型 */
    private String sectorType;

    /** 排序字段: pct_change / amount / total_mv / symbol */
    @Builder.Default
    private String sortBy = "pct_change";

    /** 排序方向: asc / desc */
    @Builder.Default
    private String sortDir = "desc";

    /** 交易日期 - 为空时自动取最近一个交易日 */
    private LocalDate tradeDate;

    /** 是否包含技术指标 */
    @Builder.Default
    private Boolean withIndicators = false;

    /** 是否包含所属池（with_pools）*/
    @Builder.Default
    private Boolean withPools = false;

    /** 是否包含概念标签（with_concepts）*/
    @Builder.Default
    private Boolean withConcepts = false;
}
