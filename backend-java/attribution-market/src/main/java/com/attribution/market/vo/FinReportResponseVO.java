package com.attribution.market.vo;

import java.util.List;

import lombok.Data;

/** 财务报表响应 */
@Data
public class FinReportResponseVO {
    private String symbol;
    private List<FinReportRowVO> reports;
}
