package com.attribution.concept.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;

import lombok.Data;

/** 概念 K 线查询条件 */
@Data
public class ConceptKlineQuery {
    private String startDate;

    private String endDate;

    @Min(value = 1, message = "天数需大于 0")
    @Max(value = 1500, message = "天数最多 1500")
    private int days = 250;
}
