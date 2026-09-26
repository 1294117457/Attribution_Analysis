package com.attribution.interfaces.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 采集任务触发请求参数
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CollectTaskRequest {

    /** 任务类型: kline_daily / daily_basic / fin_report / concept_sync */
    private String taskType;

    /** 起始日期 */
    private LocalDate startDate;

    /** 结束日期 */
    private LocalDate endDate;

    /** 股票代码过滤(为空表示全量) */
    private List<String> symbols;

    /** 周期: 1d/5d/30d/60d (kline 专用) */
    private String period;

    /** 复权类型: qfq/hfq/none (kline 专用) */
    private String adjType;

    /** 自定义扩展参_*/
    private Map<String, Object> extra;

    /** 转为 Map _Task 使用 */
    public Map<String, Object> toParams() {
        Map<String, Object> params = new HashMap<>();
        if (startDate != null) params.put("start_date", startDate.toString());
        if (endDate != null) params.put("end_date", endDate.toString());
        if (symbols != null) params.put("symbols", symbols);
        if (period != null) params.put("period", period);
        if (adjType != null) params.put("adj_type", adjType);
        if (extra != null) params.putAll(extra);
        return params;
    }
}
