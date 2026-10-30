package com.attribution.market.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;

import lombok.Data;

/** 股票列表（看板用）查询条件 */
@Data
public class StockListQuery {
    /** 关键字：代码 / 名称 / ts_code 模糊匹配 */
    private String keyword;

    @Min(value = 1, message = "页码需大于 0")
    private int page = 1;

    @Min(value = 1, message = "每页条数需大于 0")
    @Max(value = 200, message = "每页条数最多 200")
    private int pageSize = 50;

    /** 上市状态 */
    private String listStatus = "L";
}
