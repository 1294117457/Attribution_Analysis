package com.attribution.interfaces.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.util.List;

/**
 * 股票详情 - 汇总基本信息、最新行情、估值、资金流、技术指标、概念归_ */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class StockDetailVO {

    private String symbol;
    private String name;
    private String industry;
    private String market;
    private String listStatus;
    private LocalDate listDate;

    private LocalDate tradeDate;
    private Double close;
    private Double open;
    private Double high;
    private Double low;
    private Double preClose;
    private Double change;
    private Double pctChange;
    private Long volume;
    private Double amount;
    private Double turnoverRate;

    private Double pe;
    private Double peTtm;
    private Double pb;
    private Double ps;
    private Double psTtm;
    private Double dvRatio;
    private Double totalMv;
    private Double circMv;

    private Double netMfAmount;

    private List<ConceptBriefVO> concepts;
    private List<String> signals;
}
