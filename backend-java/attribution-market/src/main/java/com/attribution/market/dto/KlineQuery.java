package com.attribution.market.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;

import lombok.Data;

/** K 线查询条件 */
@Data
public class KlineQuery {
    /** 开始日期 YYYY-MM-DD */
    private String startDate;

    /** 结束日期 YYYY-MM-DD */
    private String endDate;

    @Min(value = 1, message = "条数需大于 0")
    @Max(value = 3650, message = "条数最多 3650")
    private int limit = 365;

    /** true=倒序 */
    private boolean orderDesc = true;
}
