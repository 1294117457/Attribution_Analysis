package com.attribution.user.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;

import lombok.Data;

/** 创建池操作（采集任务）入参 */
@Data
public class PoolOperationCreateRequest {
    /** kline_collect / news_fetch / factor_calc */
    private String operationType = "kline_collect";

    @Min(value = 1, message = "采集天数需大于 0")
    @Max(value = 3650, message = "采集天数最多 3650")
    private Integer days = 365;
}
