package com.attribution.market.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;

import lombok.Data;

/** 采集 K 线入参（symbol 在请求体中，与前端 collectKlines 对齐） */
@Data
public class KlineCollectRequest {
    @NotBlank(message = "股票代码不能为空")
    private String symbol;

    @Min(value = 1, message = "采集天数需大于 0")
    @Max(value = 3650, message = "采集天数最多 3650")
    private Integer days;

    private String startDate;

    private String endDate;
}
